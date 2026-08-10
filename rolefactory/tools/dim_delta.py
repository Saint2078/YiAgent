#!/usr/bin/env python3
"""按维度拆分差：那个"平均 Δ ≈ 0"是真的没效果，还是正负相消。

起因：v3 试跑 41 题的 Δ=+0.36、sd=16.31，一直被当成"效应太小、判不出来"。
但逐题一看，分差从 **+66 到 −21** —— 这不是"效果小"，是**有的题大赢、有的题大输**。
若输赢按维度分布（比如统计陷阱题稳赢、挣值分析题稳输），那么：

1. 把 41 题平均成一个 Δ，是在对**异质**效应求平均，那个数没有意义；
2. 该报的是**逐维度**结论："这套基因提升 X 维、拖累 Y 维"；
3. 而且可操作 —— 拖累哪一维，就去看是哪个槽位的基因在拖。

判据：维度内一致性。同一维度各题分差**同号**且量级接近，才谈得上"这一维有效应"；
同一维度内部就正负打架的，仍是噪声。

用法：python tools/dim_delta.py <run_id> [--holdout-only]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"
Z95 = 1.96


def load(run_id: str, holdout_only: bool) -> tuple[list[dict], set[str], str]:
    d = RUNS / run_id
    rh = RUNS / f"{run_id}-reholdout" / "results.jsonl"
    src = rh if rh.is_file() else d / "results.jsonl"
    if not src.is_file():
        raise SystemExit(f"缺逐条明细：{src}")
    rows = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    names: set[str] = set()
    rep = d / "report.json"
    if holdout_only and rep.is_file():
        hold = (json.loads(rep.read_text(encoding="utf-8")).get("scores") or {}).get("holdout") or {}
        names = {str(c) for c in (hold.get("cases") or [])}
    return rows, names, ("复核" if src is rh else "原 run")


def main() -> int:
    ap = argparse.ArgumentParser(description="按维度拆分差")
    ap.add_argument("run_id")
    ap.add_argument("--holdout-only", action="store_true")
    args = ap.parse_args()

    rows, names, src = load(args.run_id, args.holdout_only)

    scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    dim_of: dict[str, str] = {}
    for r in rows:
        case = str(r.get("case") or "")
        if names and case not in names:
            continue
        s = r.get("score")
        if isinstance(s, (int, float)):
            scores[(str(r.get("variant")), case)].append(float(s))
            dim_of[case] = str(r.get("dimension") or r.get("dimension_key") or "?")

    arms = {a for a, _ in scores}
    champs = sorted(a for a in arms if a != "baseline")
    if "baseline" not in arms or len(champs) != 1:
        raise SystemExit(f"期望「基线 + 一个冠军」两臂，实得 {sorted(arms)}")
    champ = champs[0]

    by_dim: dict[str, list[float]] = defaultdict(list)
    for (arm, case), vals in scores.items():
        if arm != champ or ("baseline", case) not in scores:
            continue
        d = st.fmean(vals) - st.fmean(scores[("baseline", case)])
        by_dim[dim_of[case]].append(d)

    all_d = [d for v in by_dim.values() for d in v]
    print(f"run {args.run_id}｜{len(all_d)} 题 / {len(by_dim)} 维｜明细来源：{src}")
    print(f"全量：Δ={st.fmean(all_d):+.2f}  sd={st.stdev(all_d):.2f}"
          f"  逐题分差范围 {min(all_d):+.1f} … {max(all_d):+.1f}\n")

    print("  维度                          题数   平均Δ    各题分差            维度内一致？")
    consistent: list[tuple[str, float, int]] = []
    for dim, ds in sorted(by_dim.items(), key=lambda x: -st.fmean(x[1])):
        m = st.fmean(ds)
        same = all(d > 0 for d in ds) or all(d < 0 for d in ds)
        # 一致 = 同号且平均分差超过维度内散布（题数 <2 谈不上一致性）
        hw = (Z95 * st.stdev(ds) / math.sqrt(len(ds))) if len(ds) > 1 else float("nan")
        strong = same and len(ds) > 1 and abs(m) > hw
        tag = "**同号且显著**" if strong else ("同号（题少）" if same else "内部打架")
        shown = "、".join(f"{d:+.0f}" for d in sorted(ds, reverse=True)[:6])
        print(f"  {dim[:26]:<28} {len(ds):>3}  {m:+7.2f}   {shown:<20} {tag}")
        if strong:
            consistent.append((dim, m, len(ds)))

    print(f"\n  {len(consistent)}/{len(by_dim)} 个维度**内部同号且超过自身散布**：")
    for dim, m, k in sorted(consistent, key=lambda x: -abs(x[1])):
        verb = "提升" if m > 0 else "拖累"
        print(f"    · {dim[:30]:<32} {verb} {abs(m):.1f} 分（{k} 题）")
    if consistent:
        print(
            "\n  读法：这些维度上的方向是稳的，但**题数少**（每维 2–3 题），"
            "\n  「维度内同号」在 2 题上有 1/4 概率纯属巧合。要当结论得先加题、并预先登记维度，"
            "\n  否则就是在 41 题里挑出好看的那几维 —— 那是事后择优，不是发现。"
        )
    print("\n  但有一件事现在就成立：**把异质效应平均成一个 Δ 会把信息抹掉**。"
          "\n  逐题分差跨 " f"{max(all_d) - min(all_d):.0f}" " 分，平均值 ≈ 0 是正负相消的结果，"
          "\n  不等于「这套基因没作用」。当前的判定口径（单个 Δ + 单个区间）答不了这个问题。")

    dead = [d for d in all_d if abs(d) < 0.01]
    if dead:
        print(f"\n  另一件现在就成立的事：**{len(dead)}/{len(all_d)} 题（{len(dead) / len(all_d):.0%}）"
              f"分差恰好为 0** —— 两臂拿一模一样的分。")
        print("  这类题对「有没有基因」完全不敏感，占着 holdout 的额度却不提供任何区分信息。"
              "\n  出题时应当过滤：一道题若连「有基因 vs 无基因」都分不开，它就量不了泛化。"
              "\n  **注意这不能用来筛现有 holdout** —— 按结果挑题是事后择优，"
              "\n  会把区间做窄成假的。它只能作用于**下一批**出题。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
