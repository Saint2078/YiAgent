#!/usr/bin/env python3
"""额度守护：Kimi 额度一恢复，就把待复核席位的 holdout 用 reps=3 跑完。

为什么要它：`reps=1` 的 holdout 判定符号不稳（PM 实测 Δ 从 −2.74 翻到 +1.46），
所以六席里五席的泛化判定目前都是「判不了」。这是目标A 唯一的卡点，而唯一的障碍
是上游额度封顶。人不在场时让它自己等、自己跑，比第二天再手动补要省一整轮等待。

每席做三件事：复核 → 用新 holdout 重写落盘基因组（adopt）→ 重新导出 yiagent bank。
最后统一刷登记表。全过程追加进 `data/watch_reholdout.log`，人回来只读这个文件。

用法：
    python tools/watch_quota_reholdout.py               # 默认每 15 分钟探一次，最多 8 小时
    python tools/watch_quota_reholdout.py --interval 600 --max-hours 4
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
    args = ap.parse_args()

    deadline = time.monotonic() + args.max_hours * 3600
    log(f"=== 守护启动：待复核 {SEATS} interval={args.interval}s max={args.max_hours}h ===")
    pending = [s for s in SEATS if not already_reheld(seat_run_id(s) or "_")]
    log(f"实际待复核：{pending or '（无，全部已复核）'}")
    if not pending:
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
    log("刷新登记表 devteam-registry.md")
    _tool(str(HERE / "build_devteam.py"), "registry")
    log(f"=== 守护结束：剩余未复核 {pending or '无'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
