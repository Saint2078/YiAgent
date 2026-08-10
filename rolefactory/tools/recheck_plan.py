#!/usr/bin/env python3
"""天花板题会不会把「只加重复就够」那个处方算歪。

`decomp_table.py` 给 Dev / Evals 开的处方是「只加重复」，依据是题间差异 σ_b ≈ 0。
但 `headroom.py` 随后发现：这两席的 holdout 里有一半题**基线已接近满分**，
两臂每次都拿同一个分 —— 分差恒为 0、题内方差也恒为 0。

于是有个必须回答的问题：**σ_b ≈ 0 是不是这些死题造成的假象？**
如果是，那"reps=9 就能判出 Evals"就是错的处方，会白烧额度。

算法：逐题拿到 (各次分数 → 题内方差, 平均分差)，然后直接算配对 t 统计量
    se(mean_delta) = √(Σ var_i(r) / n²)，其中 var_i(r) = 题 i 的分差方差 / r
并列两种口径：全部题 vs 只留基线 ≤ 95 的题（**只看基线，不看冠军**，不是事后择优）。

用法：python tools/recheck_plan.py
"""
from __future__ import annotations

import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"
Z95 = 1.96

SEATS = [("Dev", "20260809-201229-aa45e1"), ("Evals", "20260810-181341-bbaec2")]


def per_case(run_id: str):
    d = RUNS / run_id
    rh = RUNS / f"{run_id}-reholdout" / "results.jsonl"
    src = rh if rh.is_file() else d / "results.jsonl"
    rows = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    rep = json.loads((d / "report.json").read_text(encoding="utf-8"))
    names = {str(c) for c in ((rep.get("scores") or {}).get("holdout") or {}).get("cases") or []}
    acc: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        c = str(r.get("case"))
        if c in names and isinstance(r.get("score"), (int, float)):
            acc[(str(r.get("variant")), c)].append(float(r["score"]))
    champ = next(a for a, _ in acc if a != "baseline")
    out = []
    for c in sorted(names):
        b, h = acc.get(("baseline", c)), acc.get((champ, c))
        if not b or not h:
            continue
        # 题内分差方差：两臂各自的重复方差之和（两臂独立采样，配对不消掉噪声）
        vb = st.variance(b) if len(b) > 1 else 0.0
        vh = st.variance(h) if len(h) > 1 else 0.0
        out.append({"case": c, "base": st.fmean(b), "champ": st.fmean(h),
                    "delta": st.fmean(h) - st.fmean(b), "var_pair": vb + vh,
                    "reps": min(len(b), len(h))})
    return out


def stats_at(cases: list[dict], r: int) -> tuple[float, float]:
    """给定每题重复 r 次，返回 (平均分差, 半宽)。

    题间差异用**实测逐题分差的散布**，题内噪声按 1/r 缩。两者相加才是均值的方差。
    """
    n = len(cases)
    if n < 2:
        return (st.fmean([c["delta"] for c in cases]) if cases else float("nan"), float("nan"))
    deltas = [c["delta"] for c in cases]
    # 观测到的逐题分差散布里已含 reps0 次重复的残余噪声，先剥掉再按 r 重加
    r0 = max(1, min(c["reps"] for c in cases))
    var_obs = st.variance(deltas)
    var_noise0 = st.fmean([c["var_pair"] / r0 for c in cases])
    var_between = max(0.0, var_obs - var_noise0)
    var_mean = (var_between + st.fmean([c["var_pair"] / r for c in cases])) / n
    return st.fmean(deltas), Z95 * math.sqrt(var_mean)


def main() -> int:
    for seat, rid in SEATS:
        cs = per_case(rid)
        live = [c for c in cs if c["base"] <= 95.0]
        dead = [c for c in cs if c["base"] > 95.0]
        print(f"=== {seat}  run={rid} ===")
        print(f"  {len(cs)} 题｜基线 ≤95 的 {len(live)} 题｜基线 >95 的 {len(dead)} 题")
        for c in cs:
            tag = "  ← 天花板" if c["base"] > 95.0 else ""
            print(f"    {c['case'][-42:]:<44} 基线 {c['base']:6.1f}  冠军 {c['champ']:6.1f}"
                  f"  Δ={c['delta']:+6.2f}  题内方差={c['var_pair']:6.2f}{tag}")

        for label, sub in (("全部题", cs), ("只留基线≤95", live)):
            if len(sub) < 2:
                print(f"\n  {label}：只剩 {len(sub)} 题，**算不出区间**"
                      f"（自助区间要对题重采样，2 题以下没有可重采样的变异）")
                continue
            print(f"\n  {label}（n={len(sub)}）:")
            for r in (3, 9, 28, 60):
                d, hw = stats_at(sub, r)
                verdict = "判得出" if hw < abs(d) else "跨 0"
                print(f"    reps={r:<3} Δ={d:+6.2f}  半宽={hw:6.2f}  {verdict}"
                      f"   （{2 * len(sub) * r} 次评测）")
        print()

    print("读法：如果「全部题」与「只留基线≤95」给出的结论不同，"
          "\n说明处方是被天花板题带偏的 —— 那些题分差恒 0、方差恒 0，"
          "\n既压低平均 Δ 也压低散布，两头都动，方向不易预判，只能算。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
