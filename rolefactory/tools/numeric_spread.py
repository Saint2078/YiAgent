#!/usr/bin/env python3
"""numeric 的 60% 权重是摊在几条断言上的？

这是追查「加题反而让 sd 变大」（PERF.md §16）时冒出来的问题。§13 为了压堆词地板，
把 numeric 权重占比归一化到 60%。**但如果一道题只有一条 numeric 断言**，那 60% 就
全压在一个「算对 = 满分 / 算错 = 零分」的二值项上 —— 单题得分变成双峰，
方差被最大化（伯努利项的方差 ∝ 权重的平方）。

实测确有其事：产品经理那道撑起全部 Δ 的题，单条 numeric 权重 **63.0**，
基线 0/63、冠军 63/63，67 分的分差里 63 分来自这一条。

本工具量的就是：每道题有几条 numeric、单条最大权重多少、方差集中度多高。

用法：python tools/numeric_spread.py [run_id ...]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from app import objective  # noqa: E402

RUNS = ROOT / "data" / "runs"


def cases_of(run_id: str) -> list[dict]:
    p = RUNS / run_id / "state.json"
    if not p.is_file():
        return []
    st_ = json.loads(p.read_text(encoding="utf-8"))
    return [c for c in (st_.get("cases") or []) if (c.get("scoring") or "") == "objective"]


def main() -> int:
    ap = argparse.ArgumentParser(description="numeric 权重摊在几条断言上")
    ap.add_argument("runs", nargs="*")
    args = ap.parse_args()

    run_ids = args.runs or [d.name for d in sorted(RUNS.iterdir())
                            if d.is_dir() and (d / "state.json").is_file()
                            and not d.name.endswith("reholdout")]

    n_counter: Counter[int] = Counter()
    max_w: list[float] = []
    conc: list[float] = []
    total = 0
    for rid in run_ids:
        for c in cases_of(rid):
            checks = objective.normalize_checks(c.get("checks") or [])
            nums = [float(x.get("weight") or 0) for x in checks if x.get("type") == "numeric"]
            if not nums:
                continue
            total += 1
            n_counter[len(nums)] += 1
            max_w.append(max(nums))
            ws = [float(x.get("weight") or 0) for x in checks]
            tot = sum(ws) or 1.0
            # 赫芬达尔指数：权重全压一条 = 1，均摊 k 条 = 1/k。方差集中度的直接代理
            conc.append(sum((w / tot) ** 2 for w in ws))

    if not total:
        print("没有客观题")
        return 0

    print(f"客观题 {total} 道（{len(run_ids)} 个 run）\n")
    print("  每题的 numeric 断言条数：")
    for k in sorted(n_counter):
        share = n_counter[k] / total
        flag = "  ← 60% 全压一条二值项" if k == 1 else ""
        print(f"    {k} 条: {n_counter[k]:>4} 道（{share:.0%}）{flag}")

    one = n_counter.get(1, 0) / total
    print(f"\n  单条 numeric 权重：中位 {st.median(max_w):.1f}、最大 {max(max_w):.1f}")
    print(f"  权重集中度（赫芬达尔，1=全压一条）：中位 {st.median(conc):.2f}")
    print(f"\n  **{one:.0%} 的题只有一条 numeric 断言**")

    if one > 0.5:
        print(
            "\n结论：60% 的 numeric 占比，在多数题上等于「一条断言定六成分数」。\n"
            "  单题得分因此接近双峰（算对 / 算错），题间方差被放大 —— 这解释了 §16 里\n"
            "  「题量加 7 倍、sd 从 4.23 涨到 16.31」：不是题变难了，是**尺子的方差**变大了。\n"
            "  可选的一刀：出题时要求 ≥2 条 numeric，让 60% 摊开（30%+30%）。\n"
            "  **但别当成必然收益** —— 同一道题的两个数往往出自同一条计算链（先算率再算阈值），\n"
            "  高度相关的话摊开压不下多少方差。这条得实测，不能按独立假设算。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
