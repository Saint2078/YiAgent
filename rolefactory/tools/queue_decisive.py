#!/usr/bin/env python3
"""等额度，然后跑**唯一一席值得花额度**的高重复复核：Evals。

选席位经过两道筛，不是只看便宜：

一、`decomp_table.py`（方差分解）：只有 Dev 与 Evals 的**题间差异 ≈ 0**，
    加重复就能把区间压到 |Δ| 以下，一道新题都不用出。其余四席的下限已高于 |Δ|。

二、`headroom.py`（天花板）：这两席的基线都贴着满分（Dev 94.9、Evals 94.8），
    平均只剩 5 分可涨、却有 95 分可跌 —— 量尺**上下不对称**，量出来的 Δ 系统性偏负。
    于是两席的处境完全不同：

    · Dev 的 Δ = **−0.87**（负）。在一把偏负的尺子上量出负数，
      分不清是"基因有害"还是"截断偏"。**判出来也不能得结论**，所以不值得花。
    · Evals 的 Δ = **+1.71**（正）。偏是往负的方向偏，却仍量出正数 ——
      这叫**保守估计**：真实效应至少这么大。判出来就是可辩护的结论。

所以只排 Evals，且把重复数从 9 抬到 15：reps=9 的半宽 1.69 对 |Δ|=1.71，
只差 0.02，属于"擦边判过"，任何漂移都会让它重新跨 0。

    Evals   reps=15 × 现有 6 题 = 180 次评测（半宽约 1.3，留出余量）

**仍然不保证赢**：+1.71 有可能就是收窄后仍跨 0。那也是结论 —— 明确的"效应小于
可测量下限"，比"判不了"有信息。

用法：python tools/queue_decisive.py [--probe-every 600]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# (席位, reps, 预计评测数)
# Dev 曾在这张表里（reps=28、336 次），后被拿掉：它的 Δ 是负的，而尺子本身偏负，
# 判出来也分不清是基因有害还是截断偏 —— 花 336 次买一个不能用的结论。
PLAN = [("Evals", 15, 180)]


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def seat_run(seat: str) -> str | None:
    p = ROOT.parent / "console" / "_workbench" / "AgentTeam" / "Develop" / seat / "genome.json"
    if not p.is_file():
        return None
    return (json.loads(p.read_text(encoding="utf-8")).get("source") or {}).get("run_id")


def main() -> int:
    ap = argparse.ArgumentParser(description="等额度后跑高重复复核")
    ap.add_argument("--probe-every", type=int, default=600)
    args = ap.parse_args()

    log(f"排队：{'、'.join(f'{s} reps={r}（{e}次）' for s, r, e in PLAN)}")
    for seat, reps, evals in PLAN:
        run_id = seat_run(seat)
        if not run_id:
            log(f"{seat}: 没有落盘基因组，跳过")
            continue
        log(f"=== {seat} run={run_id} reps={reps}（约 {evals} 次评测）===")
        rc = subprocess.run(
            [sys.executable, str(HERE / "run_reholdout.py"), run_id,
             "--reps", str(reps), "--seat", seat,
             "--wait-quota", "--probe-every", str(args.probe_every)],
            cwd=str(ROOT),
        ).returncode
        if rc == 2:
            # 额度中途又断（探针通过不代表跑得完一轮）。停在这里，别把后面那席也烧成半截。
            log(f"{seat}: 额度中途耗尽，队列中止（后面的席位没动）")
            return 2
        if rc != 0:
            log(f"{seat}: 失败 rc={rc}，队列中止")
            return rc
        log(f"{seat}: 完成并已传导到下游")
        # 复核换了数，处方表跟着变 —— 打一次给日志留痕
        subprocess.run([sys.executable, str(HERE / "decomp_table.py")], cwd=str(ROOT))
    log("=== 队列结束 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
