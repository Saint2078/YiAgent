#!/usr/bin/env python3
"""筛题门槛的空跑：拿历史题组算一遍「要是当初开着门槛，会扔掉哪些题」。

这是花额度之前唯一能做的验证。门槛会**删题**，删多了会把维度删空、把 holdout 削到
判不了 —— 单测钉住了护栏逻辑，但只有真实题组能回答"实际会扔多少"。

一处口径必须说清：空跑用的是历史报告里 `baseline.by_case` 的分数，那份分数**同时**
参与了当初的 Δ 计算。真跑时门槛用的是独立采样（`pipeline.PROBE_REP`），
所以空跑只能估"扔多少道"，不能用来预测真跑后的 Δ。

用法：python tools/gate_dryrun.py [--ceiling 90]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from app import roles  # noqa: E402

RUNS = ROOT / "data" / "runs"
SEATS = [
    ("Product", "20260809-191310-a7b2bd"), ("PM", "20260810-185143-6ea6f5"),
    ("Architect", "20260809-194427-8cfdb4"), ("Dev", "20260809-201229-aa45e1"),
    ("DevOps", "20260809-203635-e70531"), ("Evals", "20260810-181341-bbaec2"),
    ("v3试跑(41题)", "20260810-213118-209063"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="筛题门槛空跑")
    ap.add_argument("--ceiling", type=float, default=90.0)
    ap.add_argument("--holdout-per-dim", type=int, default=0,
                    help="0 = 沿用该 run 当初的设置")
    args = ap.parse_args()

    print(f"门槛：基线 >{args.ceiling:g} 分的题扔掉，每维最多扔一半\n")
    print("  席位            总题  超标  扔掉  留下  holdout(原→新)  维度数(原→新)")
    for seat, rid in SEATS:
        d = RUNS / rid
        rep_p, st_p = d / "report.json", d / "state.json"
        if not (rep_p.is_file() and st_p.is_file()):
            continue
        report = json.loads(rep_p.read_text(encoding="utf-8"))
        state = json.loads(st_p.read_text(encoding="utf-8"))
        cases = [c for c in (state.get("cases") or []) if c.get("dimension_key")]
        if not cases:
            continue

        # 基线逐题分：train 段来自 scores.baseline_no_genes，holdout 段来自 scores.holdout.baseline
        sc = report.get("scores") or {}
        by_case: dict[str, float] = {}
        for blk in ((sc.get("baseline_no_genes") or {}),
                    ((sc.get("holdout") or {}).get("baseline") or {})):
            for k, v in (blk.get("by_case") or {}).items():
                if isinstance(v, (int, float)):
                    by_case[str(k)] = float(v)
        covered = [c for c in cases if c["id"] in by_case]
        if not covered:
            print(f"  {seat:<14} —— 报告里没有逐题基线分，空跑不了")
            continue

        hpd = args.holdout_per_dim or int((report.get("params") or {}).get("holdout_per_dim") or 1)
        keep, dropped = roles.drop_saturated(
            covered, by_case, ceiling=args.ceiling, reserve_per_dim=1 + hpd
        )
        _, hold_old = roles.split_holdout(covered, per_dim=hpd)
        _, hold_new = roles.split_holdout(keep, per_dim=hpd)
        dims_old = len({c["dimension_key"] for c in covered})
        dims_new = len({c["dimension_key"] for c in keep})
        over = sum(1 for c in covered if by_case[c["id"]] > args.ceiling)
        warn = ""
        if dims_new < dims_old:
            warn = "  ⚠ 维度被削"
        elif len(hold_new) < len(hold_old):
            warn = "  ⚠ holdout 反而变少"
        elif over and not dropped:
            warn = f"  空转（{over} 道超标但无余量）"
        print(f"  {seat:<14} {len(covered):>4}  {over:>4}  {len(dropped):>4}  {len(keep):>4}"
              f"  {len(hold_old):>6} → {len(hold_new):<5}"
              f"  {dims_old:>6} → {dims_new:<6}{warn}")

    print("\n  护栏检查：出现「维度被削」或「holdout 反而变少」都属实现缺陷 ——"
          "\n  门槛的目的是提高有效题量，把 holdout 削小是净亏（空跑第一版正是这样："
          "\n  Product 的 holdout 从 5 掉到 1，靠 reserve_per_dim 修掉）。")
    print("  「空转」不是缺陷，是门槛在说「先多出题，再谈筛题」：每维保留 1+holdout_per_dim 道后"
          "\n  没有余量可扔。要让它生效，per_dim 出题量得明显高于 holdout_per_dim+1。")
    print("  注：空跑的基线分与当初 Δ 同源，只能估「扔多少道」，不能预测真跑后的 Δ。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
