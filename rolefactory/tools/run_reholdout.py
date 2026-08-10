#!/usr/bin/env python3
"""对已完成的 run 单独重跑 holdout，并把复核结果传导到所有下游产物。

`POST /api/run/{id}/reholdout` 是**同步**接口，一跑十几分钟。用 shell 的后台作业发它
会连不住：作业随父进程一起死，请求被丢掉，服务端也跟着取消。所以单独写个驱动脚本，
由脚本自己持有连接。

默认跑完就把四处一起刷（卡片 / 落盘基因组 / 席位基因库 / 载体）—— 少刷一处不报错，
只有 `verify_chain.py` 会发现（实测断过一次五席）。只想看数不想改链路就加 `--no-adopt`。

用法：
    python tools/run_reholdout.py <run_id> [--reps 3] [--seat PM] [--no-adopt]
    python tools/run_reholdout.py <run_id> --reps 3 --wait-quota   # 额度封顶时挂着等
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = "http://127.0.0.1:8790"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def post(path: str, body: dict[str, Any], timeout: int) -> tuple[int, Any]:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:500]


def tool(*argv: str) -> bool:
    r = subprocess.run(
        [sys.executable, *argv], cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    for ln in (r.stdout or "").splitlines():
        print(f"    | {ln}", flush=True)
    if r.returncode != 0:
        log(f"  ! 失败 rc={r.returncode}: {(r.stderr or '')[-400:]}")
    return r.returncode == 0


def wait_for_quota(every: int) -> bool:
    """探到额度可用才返回 True。

    探针只证明「密钥和通道没坏」，**不保证跑得完一轮** —— 实测 05:58 探针通过、
    06:00 发复核就吃 403，因为上一轮实跑已经把余量用光。所以探通之后仍可能中途 503，
    那种情况下服务端拒绝落盘，重跑即可。
    """
    probe = str(HERE / "quota_probe.py")
    n = 0
    while True:
        r = subprocess.run([sys.executable, probe], cwd=str(ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            log(f"额度可用（探了 {n + 1} 次）：{(r.stdout or '').strip()[:80]}")
            return True
        if n % 6 == 0:  # 每小时报一次，别把日志刷满
            waited = n * every // 60
            log(
                f"额度仍封顶（已等 {waited} 分钟）：{(r.stdout or '').strip()[:60]}"
                if waited else f"额度封顶，开始等：{(r.stdout or '').strip()[:60]}"
            )
        n += 1
        time.sleep(every)


def main() -> int:
    ap = argparse.ArgumentParser(description="重跑 holdout 并传导结果")
    ap.add_argument("run_id")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seat", default=None, help="给了席位名就顺带 adopt + 重导 bank/实体")
    ap.add_argument("--no-adopt", action="store_true", help="只复核，不改下游产物")
    ap.add_argument("--wait-quota", action="store_true",
                    help="额度封顶时每 10 分钟探一次，恢复后再跑")
    ap.add_argument("--probe-every", type=int, default=600, help="探额度间隔秒")
    args = ap.parse_args()

    if args.wait_quota and not wait_for_quota(args.probe_every):
        return 2

    log(f"复核开始 run={args.run_id} reps={args.reps}")
    t0 = time.monotonic()
    status, body = post(f"/api/run/{args.run_id}/reholdout", {"reps": args.reps}, 7200)
    dt = time.monotonic() - t0

    if status == 503:
        # 服务端把额度耗尽单独抬成 503：不是数据问题，别把它当失败结论记下来
        log(f"额度中途耗尽（503），{dt:.0f}s 后中止：{str(body)[:200]}")
        return 2
    if status != 200 or not isinstance(body, dict):
        log(f"复核失败 status={status} 用时 {dt:.0f}s：{str(body)[:300]}")
        return 1

    p = body.get("paired") or {}
    log(
        f"复核完成（{dt:.0f}s）：Δ(加权)={body.get('delta_weighted')} · "
        f"Δ(配对)={p.get('mean_delta')} CI95={p.get('mean_delta_ci95')} "
        f"sd={p.get('sd_delta')} n={p.get('cases')} significant={p.get('significant')}"
        "  ← 区间属于配对 Δ"
    )

    log("方差分解（这才是 reps≥2 换来的东西）：")
    tool(str(HERE / "variance_decomp.py"), args.run_id)

    if args.no_adopt or not args.seat:
        log("未传导到下游产物（--no-adopt 或没给 --seat）。卡片也没重生成。")
        return 0

    log(f"传导结果到下游：{args.seat}")
    tool(str(HERE / "genome_card.py"), args.run_id)
    if not tool(str(HERE / "build_devteam.py"), "adopt", args.seat, args.run_id):
        return 1
    tool(str(HERE / "build_devteam.py"), "registry")
    tool(str(ROOT.parent / "scripts" / "build_agent_entities.py"), "--refresh")
    ok = tool(str(ROOT.parent / "scripts" / "verify_chain.py"))
    log(f"链路对账：{'6/6 自洽' if ok else '**断链**，见上面输出'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
