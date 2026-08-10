#!/usr/bin/env python3
"""基线还剩多少分可涨：holdout 里有多少题**根本没有空间**显示提升。

这是追"加题为什么没提升判定力"（PERF.md §16）追到的底。逐题看分差时发现
大量分差**恰好为 0**，而且这些题的分数都在 **75–100** —— 两臂都接近满分。
不是基因没用，是**题太容易，天花板压住了**：基线已经拿 96 分，
再好的基因最多也只能多拿 4 分。这类题占着 holdout 额度，却量不出任何东西。

口径：一道题的**可涨空间** = 100 − 基线得分。要能观测到 δ 分的提升，
至少得有 δ 分的空间。所以"能测出 5 分提升的题"= 基线 ≤ 95 的题。

天花板效应还有个连带后果：它同时压低平均 Δ（饱和题贡献 0）**并**压低 sd，
所以它不会在"Δ/sd"上留下明显痕迹 —— 只能靠看分数分布发现。

用法：python tools/headroom.py [--min-gain 5]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"

SEATS = [
    ("Product", "20260809-191310-a7b2bd"), ("PM", "20260810-185143-6ea6f5"),
    ("Architect", "20260809-194427-8cfdb4"), ("Dev", "20260809-201229-aa45e1"),
    ("DevOps", "20260809-203635-e70531"), ("Evals", "20260810-181341-bbaec2"),
    ("v3试跑(41题)", "20260810-213118-209063"),
]


def holdout_scores(run_id: str) -> tuple[dict[str, float], dict[str, float]]:
    """题 → 基线均分、题 → 冠军均分（只取 holdout）。"""
    d = RUNS / run_id
    rh = RUNS / f"{run_id}-reholdout" / "results.jsonl"
    src = rh if rh.is_file() else d / "results.jsonl"
    if not src.is_file():
        return {}, {}
    rows = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    rep = json.loads((d / "report.json").read_text(encoding="utf-8"))
    names = {str(c) for c in ((rep.get("scores") or {}).get("holdout") or {}).get("cases") or []}

    acc: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        c = str(r.get("case"))
        if c in names and isinstance(r.get("score"), (int, float)):
            acc[(str(r.get("variant")), c)].append(float(r["score"]))
    arms = {a for a, _ in acc}
    champs = [a for a in arms if a != "baseline"]
    if not champs:
        return {}, {}
    champ = champs[0]
    base = {c: st.fmean(v) for (a, c), v in acc.items() if a == "baseline"}
    ch = {c: st.fmean(v) for (a, c), v in acc.items() if a == champ}
    return base, ch


def main() -> int:
    ap = argparse.ArgumentParser(description="基线可涨空间与天花板题占比")
    ap.add_argument("--min-gain", type=float, default=5.0,
                    help="想观测到的最小提升（分）；空间不足这个数的题算测不出")
    args = ap.parse_args()
    g = args.min_gain

    print(f"想观测到 ≥{g:g} 分的提升，题目至少要留 {g:g} 分空间（即基线 ≤ {100 - g:g}）\n")
    print("  席位            题数  基线均分  基线中位  满分题  空间不足  可用题  有效题占比")
    rows_out = []
    for seat, rid in SEATS:
        base, ch = holdout_scores(rid)
        if not base:
            continue
        vals = list(base.values())
        full = sum(1 for v in vals if v >= 99.99)
        tight = sum(1 for v in vals if v > 100 - g)
        usable = len(vals) - tight
        rows_out.append((seat, len(vals), st.fmean(vals), st.median(vals), full, tight, usable))
        print(f"  {seat:<14} {len(vals):>4}  {st.fmean(vals):>7.1f}  {st.median(vals):>7.1f}"
              f"  {full:>5}  {tight:>7}  {usable:>5}  {usable / len(vals):>8.0%}")

    tot_n = sum(r[1] for r in rows_out)
    tot_ok = sum(r[6] for r in rows_out)
    print(f"\n  合计 {tot_n} 题，其中 {tot_n - tot_ok} 题空间不足 {g:g} 分"
          f"（{(tot_n - tot_ok) / tot_n:.0%}），可用 {tot_ok} 题（{tot_ok / tot_n:.0%}）")

    pilot = next((r for r in rows_out if "41" in r[0]), None)
    if pilot:
        print(
            f"\n  这解释了 §16 的一半：v3 试跑名义上 {pilot[1]} 题，但按「留得下 {g:g} 分」算"
            f"只有 {pilot[6]} 题真的能量到东西。\n"
            "  加题加的是**名义题量**，不是**有效题量** —— 而判定力只认后者。"
        )
    print(
        "\n  出题侧可以立刻加的一道门槛：**先用无基因基线试答，基线得分 > 90 的题直接弃用**。\n"
        "  这道门槛不花额外额度（基线本来就要跑），也不涉及看结果挑题 —— 它只看基线，\n"
        "  不看冠军，因此不构成事后择优。\n"
        "  **不能夸大**：去掉天花板题会让平均 Δ 和 sd 同时变大，净收益要实测；\n"
        "  它保证的是「题有能力显示差异」，不保证「差异存在」。"
    )

    print("\n" + "=" * 72)
    print("上行空间 vs 下行空间：基线越接近满分，Δ 越会被**系统性压成负的**\n")
    print("  一道基线 95 分的题，冠军最多只能 +5，却可以 −95。这不是方差，是**偏**：")
    print("  同一套基因，放在高基线题上量出来的 Δ 会比真实效应更负。\n")
    print("  席位            基线均分  平均可涨(上行)  平均可跌(下行)  上行/下行  实测Δ")
    for seat, rid in SEATS:
        base, ch = holdout_scores(rid)
        if not base:
            continue
        up = st.fmean([100.0 - v for v in base.values()])
        down = st.fmean(list(base.values()))
        deltas = [ch[c] - base[c] for c in base if c in ch]
        ratio = up / down if down else float("inf")
        flag = "  ← 上行不足下行的 1/10" if ratio < 0.1 else ""
        print(f"  {seat:<14} {st.fmean(list(base.values())):>7.1f}  {up:>13.1f}  {down:>13.1f}"
              f"  {ratio:>8.2f}  {st.fmean(deltas):+6.2f}{flag}")

    print(
        "\n  这一条直接影响怎么读 Dev 那个负号：Dev 基线均分 94.9，平均只剩 5.1 分可涨、"
        "\n  却有 94.9 分可跌。它实测 Δ=−0.87，**不足以说明这套基因有害** —— 在这种"
        "\n  上下不对称的量尺上，即便基因完全无害，量出来的 Δ 也倾向为负"
        "\n  （随机波动在上方被截断、在下方不被截断）。"
        "\n\n  所以「判得出 Δ=−0.87」和「这套基因不如基线」不是一回事。前者是测量结论，"
        "\n  后者需要一把上下对称的尺子 —— 也就是基线别贴着天花板。"
        "\n  **这是推断（中等置信度）**：截断偏的方向可以从构造上说清，但具体偏多少要模拟或实测。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
