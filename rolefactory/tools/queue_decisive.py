#!/usr/bin/env python3
"""等额度，然后按「最便宜的可判席位」顺序跑高重复复核。

排队顺序不是拍的，是 `tools/decomp_table.py` 算出来的：方差分解显示 Dev 与 Evals 的
**题间差异 ≈ 0**（噪声全在每题内部），所以只加重复就能把区间压到 |Δ| 以下，
一道新题都不用出。其余四席题间差异撑起的下限已高于 |Δ|，加重复无用、必须先扩题库。

    Evals   reps=9  × 现有 6 题 = 108 次评测
    Dev     reps=28 × 现有 6 题 = 336 次评测

先跑便宜的：万一额度只够一席，也能换到一个结论。

**这不是「一定能判出更强」**：区间收窄到 |Δ| 以下只说明「判得出这个量级」，
结果可能是站得住、也可能是明确的「不如基线」（Dev 的 Δ 是负的）。两者都算结论。

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

# (席位, reps, 预计评测数)。顺序 = 从便宜到贵。
PLAN = [("Evals", 9, 108), ("Dev", 28, 336)]


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
