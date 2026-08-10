#!/usr/bin/env python3
"""额度守护：Kimi 额度一恢复，先补完五席 holdout 复核，再跑一次有界的 v3 试跑。

为什么要它：`reps=1` 的 holdout 判定符号不稳（PM 实测 Δ 从 −2.74 翻到 +1.46），
所以六席里五席的泛化判定目前都是「判不了」。这是目标A 唯一的卡点，而唯一的障碍
是上游额度封顶。人不在场时让它自己等、自己跑，比第二天再手动补要省一整轮等待。

每席做三件事：复核 → 用新 holdout 重写落盘基因组（adopt）→ 重新导出 yiagent bank。
最后统一刷登记表。全过程追加进 `data/watch_reholdout.log`，人回来只读这个文件。

**复核之后还有一步（`--pilot`）**：旧 run 的 holdout 只有 6 道，判定力核算说这个题量
怎么都判不了（MDE 1.72 > 实测效应 1.41，PERF.md §10.1）。所以复核的价值只是把
「reps=1 的噪声结论」换成有区间的诚实结论，**不可能**得出「更强」。真正能结案的是按
新口径（v3）重跑一轮：`per_dim=8 / holdout_per_dim=7` → holdout 42 道，MDE≈1.07。

试跑刻意设成**只跑、不采纳**：无人值守时不动交付链（不改 genome.json / bank / vector），
只把冠军分、holdout Δ、95% 区间与 sd 写进日志和 `genome_card`。人看了再决定要不要采纳。
默认只跑 **1 席**（额度是别人的钱，不替人花第二份）。

用法：
    python tools/watch_quota_reholdout.py               # 默认每 15 分钟探一次，最多 8 小时
    python tools/watch_quota_reholdout.py --interval 600 --max-hours 4
    python tools/watch_quota_reholdout.py --pilot PM    # 复核完再跑一次 PM 的 v3 试跑
    python tools/watch_quota_reholdout.py --no-reholdout --pilot PM   # 只跑试跑
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOG = ROOT / "data" / "watch_reholdout.log"
SEATS_DIR = ROOT.parent / "console" / "_workbench" / "AgentTeam" / "Develop"
BASE = "http://127.0.0.1:8790"
# PM 已在 08-10 复核过（reps=3），不重复烧额度
SEATS = ["Product", "Architect", "Dev", "DevOps", "Evals"]


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _post(path: str, payload: dict, timeout: float) -> tuple[int, dict | str]:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600].decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:300]


def quota_ok() -> bool:
    status, body = _post("/api/perf/probe", {"n": 1, "concurrency": 1, "max_tokens": 512}, 180)
    return status == 200 and isinstance(body, dict) and int(body.get("ok") or 0) > 0


def seat_run_id(seat: str) -> str:
    p = SEATS_DIR / seat / "genome.json"
    if not p.is_file():
        return ""
    return str((json.loads(p.read_text(encoding="utf-8")).get("source") or {}).get("run_id") or "")


def already_reheld(run_id: str) -> bool:
    return (ROOT / "data" / "runs" / run_id / "reholdout.json").is_file()


def _get(path: str, timeout: float = 30) -> tuple[int, dict | str]:
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400].decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:300]


def pilot(seat: str) -> str:
    """按 v3 口径与新题量跑一次**不采纳**的试跑，只把结论写进日志。

    要回答的是 PERF.md §15.1 记账的那个问题：抬 numeric 占比到底会不会改善判定力 ——
    那要新口径下的 sd，而 sd 只能实跑量。顺带给出 42 道 holdout 的真实区间。
    """
    sys.path.insert(0, str(HERE))
    from build_devteam import RUN_PARAMS, TEAM  # noqa: PLC0415 复用跑参，避免两处漂移

    meta = next((m for m in TEAM if m["seat"] == seat), None)
    if not meta:
        log(f"  试跑：未知席位 {seat}，可选 {[m['seat'] for m in TEAM]}")
        return "skip"
    payload = {"role": meta["factory_role"], **RUN_PARAMS}
    log(
        f"  试跑 {seat}／{meta['factory_role']}：per_dim={payload.get('per_dim')} "
        f"holdout_per_dim={payload.get('holdout_per_dim')} variants={payload.get('variants_per_gen')}"
    )
    status, body = _post("/api/run", payload, 120)
    if status != 200 or not isinstance(body, dict):
        log(f"  试跑启动失败 status={status} {str(body)[:300]}")
        return "fail"
    rid = str(body.get("run_id") or "")
    log(f"  试跑 run={rid}，开始轮询（不采纳，只记结论）")

    while True:
        time.sleep(30)
        st_code, st = _get(f"/api/run/{rid}")
        if st_code != 200 or not isinstance(st, dict):
            log(f"  试跑轮询异常 status={st_code} {str(st)[:200]}")
            continue
        state = str(st.get("status") or "")
        prog = st.get("progress") or {}
        log(
            f"    {rid} {state}/{st.get('phase')} "
            f"eval={prog.get('eval_done')}/{prog.get('eval_total')} "
            f"failed={prog.get('eval_failed')} wall={st.get('wall_seconds')}s"
        )
        if state in ("done", "error", "aborted", "failed"):
            break
    if state != "done":
        log(f"  试跑未完成：{state}")
        return "fail"

    _tool(str(HERE / "genome_card.py"), rid)
    code, rep = _get(f"/api/run/{rid}?full=1", timeout=60)
    if code == 200 and isinstance(rep, dict):
        hold = rep.get("holdout") or {}
        paired = hold.get("paired") or {}
        log(
            f"  试跑完成 {rid}：train Δ={(rep.get('champion') or {}).get('delta_weighted')} "
            f"holdout Δ={hold.get('delta_weighted')} "
            f"CI95={paired.get('mean_delta_ci95')} sd={paired.get('sd_delta')} "
            f"cases={len(hold.get('cases') or [])} scorer=v{(rep.get('scoring') or {}).get('scorer_version')}"
        )
        log("  注意：**未采纳**。要采纳跑 `python tools/build_devteam.py adopt "
            f"{seat} {rid}`，然后重导 bank 与实体。")
    return "done"


def _tool(*argv: str) -> bool:
    """跑同目录下的工具脚本，输出进日志。"""
    r = subprocess.run(
        [sys.executable, *argv], cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    for ln in (r.stdout or "").splitlines():
        log(f"      | {ln}")
    if r.returncode != 0:
        log(f"      ! 失败 rc={r.returncode}: {(r.stderr or '')[-400:]}")
    return r.returncode == 0


def do_seat(seat: str, reps: int) -> str:
    """返回结果标签：done / skip / fail / quota_down。"""
    run_id = seat_run_id(seat)
    if not run_id:
        log(f"  {seat}: 没有落盘基因组，跳过")
        return "skip"
    if already_reheld(run_id):
        log(f"  {seat}: 已有 reholdout.json，跳过（{run_id}）")
        return "skip"

    log(f"  {seat}: 复核开始 run={run_id} reps={reps}")
    status, body = _post(f"/api/run/{run_id}/reholdout", {"reps": reps}, 3600)
    if status == 503:
        # 服务端把额度耗尽单独抬成 503：这不是数据问题，等下一轮
        log(f"  {seat}: 额度中途耗尽（503），本轮中止：{str(body)[:200]}")
        return "quota_down"
    if status != 200 or not isinstance(body, dict):
        log(f"  {seat}: 复核失败 status={status} {str(body)[:300]}")
        return "fail"

    paired = (body.get("paired") or {})
    log(
        f"  {seat}: 复核完成 Δ={body.get('delta_weighted')} "
        f"CI95={paired.get('mean_delta_ci95')} significant={paired.get('significant')}"
    )
    # 复核结果要进落盘基因组与登记表，否则判定只活在 run 目录里
    if not _tool(str(HERE / "build_devteam.py"), "adopt", seat, run_id):
        return "fail"
    _tool(str(HERE / "export_yiagent_bank.py"), "--seat", seat)
    return "done"


def main() -> int:
    ap = argparse.ArgumentParser(description="额度恢复即自动复核五席 holdout")
    ap.add_argument("--interval", type=int, default=900, help="探测间隔秒（默认 900）")
    ap.add_argument("--max-hours", type=float, default=8.0, help="最长守候小时数")
    ap.add_argument("--reps", type=int, default=3, help="holdout 重复次数")
    ap.add_argument(
        "--pilot", metavar="席位", default=None,
        help="复核完再按 v3 口径跑一次该席位的试跑（只跑不采纳；旧 6 道 holdout 判不了）",
    )
    ap.add_argument("--no-reholdout", action="store_true", help="跳过复核，直接做试跑")
    args = ap.parse_args()

    deadline = time.monotonic() + args.max_hours * 3600
    log(
        f"=== 守护启动：待复核 {SEATS} interval={args.interval}s max={args.max_hours}h "
        f"pilot={args.pilot or '无'} ==="
    )
    pending = [] if args.no_reholdout else [
        s for s in SEATS if not already_reheld(seat_run_id(s) or "_")
    ]
    log(f"实际待复核：{pending or '（无）'}")
    if not pending and not args.pilot:
        return 0

    round_no = 0
    while time.monotonic() < deadline and pending:
        round_no += 1
        if not quota_ok():
            log(f"第 {round_no} 轮：额度仍封顶，{args.interval}s 后重试（剩 {len(pending)} 席）")
            time.sleep(args.interval)
            continue

        log(f"第 {round_no} 轮：额度恢复，开始复核 {pending}")
        for seat in list(pending):
            result = do_seat(seat, args.reps)
            if result == "quota_down":
                log("额度中途耗尽，回到等待")
                break
            if result in ("done", "skip"):
                pending.remove(seat)
        if pending:
            time.sleep(args.interval)

    # 判定口径变了，登记表统一重刷一次
    if not args.no_reholdout:
        log("刷新登记表 devteam-registry.md")
        _tool(str(HERE / "build_devteam.py"), "registry")

    # 复核完再做有界试跑：额度可能在复核里又耗尽，所以先探一次再决定
    if args.pilot and time.monotonic() < deadline:
        while time.monotonic() < deadline:
            if quota_ok():
                pilot(args.pilot)
                break
            log(f"试跑等额度：{args.interval}s 后重试")
            time.sleep(args.interval)
        else:
            log("试跑未开始：守候时间用尽，额度始终未恢复")

    log(f"=== 守护结束：剩余未复核 {pending or '无'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
