#!/usr/bin/env python3
"""每题分差的方差，是哪一类断言贡献的。

§16 记了一个没解释清的现象：holdout 从 6 题加到 41 题，sd 从 4.23 涨到 **16.31**，
判定力反而变差。当时归因给「堆词地板压低 → 动态范围扩大」—— 那是个说法，不是测量。

这里做真正的测量：把每题分差按断言类型拆开，看**方差**主要来自哪一类。
做法是用评测时就落盘的逐条得分（`results.jsonl` 里每条 check 的 0..1 比例分），
按类型加权求和，得到"只看这一类断言"的分差，再看它的 sd。

关键一列是「去掉 numeric 之后的 sd」：如果 numeric 是方差主项，去掉它 sd 会大幅下降，
那么 §13 那刀（把 numeric 权重抬到 60%）就是自己给判定力挖的坑 —— 分辨率买到了，
方差也一起买了。

用法：python tools/variance_by_check.py <run_id> [--holdout-only]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"


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


def by_type(row: dict) -> dict[str, float]:
    """这一次评测里，每类断言实际拿到的分（已按总权重折算到 100 分制）。"""
    checks = row.get("checks") or []
    tot = sum(float(c.get("weight") or 0) for c in checks) or 1.0
    out: dict[str, float] = defaultdict(float)
    for c in checks:
        w = float(c.get("weight") or 0)
        s = float(c.get("score") or 0)
        out[str(c.get("type"))] += w * s / tot * 100.0
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="每题分差的方差按断言类型拆解")
    ap.add_argument("run_id")
    ap.add_argument("--holdout-only", action="store_true")
    args = ap.parse_args()

    rows, names, src = load(args.run_id, args.holdout_only)

    # (臂, 题) → 各类型得分的多次均值
    acc: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    for r in rows:
        case = str(r.get("case") or "")
        if names and case not in names:
            continue
        acc[(str(r.get("variant")), case)].append(by_type(r))

    arms = {a for a, _ in acc}
    if "baseline" not in arms:
        raise SystemExit(f"没有基线臂：{sorted(arms)}")
    champs = sorted(a for a in arms if a != "baseline")
    if len(champs) != 1:
        raise SystemExit(f"期望恰好一个非基线臂，实得 {champs}")
    champ = champs[0]

    cases = sorted({c for a, c in acc if a == champ and ("baseline", c) in acc})
    types = sorted({t for v in acc.values() for d in v for t in d})

    def mean_of(arm: str, case: str, t: str) -> float:
        return st.fmean([d.get(t, 0.0) for d in acc[(arm, case)]])

    per_type: dict[str, list[float]] = {t: [] for t in types}
    totals: list[float] = []
    no_num: list[float] = []
    for case in cases:
        tot_d = 0.0
        for t in types:
            d = mean_of(champ, case, t) - mean_of("baseline", case, t)
            per_type[t].append(d)
            tot_d += d
        totals.append(tot_d)
        no_num.append(tot_d - (per_type["numeric"][-1] if "numeric" in per_type else 0.0))

    n = len(cases)
    print(f"run {args.run_id}｜{n} 题｜明细来源：{src}"
          f"｜{'只看 holdout' if names else '全部题'}")
    print(f"\n  合计    Δ={st.fmean(totals):+7.2f}  sd={st.stdev(totals):6.2f}" if n > 1 else "")
    print("\n  断言类型            平均分差   分差 sd   占总方差")
    var_tot = st.variance(totals) if n > 1 else 0.0
    for t in sorted(types, key=lambda x: -(st.variance(per_type[x]) if n > 1 else 0)):
        v = st.variance(per_type[t]) if n > 1 else 0.0
        share = (v / var_tot) if var_tot else 0.0
        print(f"  {t:<18} {st.fmean(per_type[t]):+8.2f}  {st.stdev(per_type[t]) if n > 1 else 0:7.2f}"
              f"   {share:6.0%}")
    print("  （各类型方差占比之和可以不等于 100% —— 类型之间存在协方差，"
          "\n    一个答案算错往往同时丢 numeric 和相关的 must_include）")

    if n > 1 and "numeric" in per_type:
        sd_all, sd_non = st.stdev(totals), st.stdev(no_num)
        print(f"\n  去掉 numeric 之后：Δ={st.fmean(no_num):+.2f}  sd={sd_non:.2f}"
              f"（原 {sd_all:.2f}，{'降' if sd_non < sd_all else '升'} {abs(1 - sd_non / sd_all):.0%}）")
        if sd_non < sd_all * 0.7:
            print("  → numeric 是方差主项。§13 把它的权重抬到 60%，分辨率买到了，方差也一起买了。")
        else:
            print("  → numeric **不是**方差主项，sd 大另有来源。§13 那刀不背这个锅。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
