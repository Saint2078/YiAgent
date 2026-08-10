#!/usr/bin/env python3
"""逐题看分差：哪道题在撑起整个 Δ 和整个区间。

为什么要看：方差分解给的是**汇总**的 σ_b（题间差异）。产品经理一席 σ_b=33.48，
在 0–100 的分数尺上大得离谱 —— 这种量级通常不是"题目本来就有难有易"，
而是**一两道题的行为和其余完全不同**。如果那一两道题本身有毛病（断言退化、
只剩一个 numeric 权重、题面自相矛盾），那么修题就能白捡判定力，不用加题也不用加重复。

判据：留一法。去掉某题后 |Δ| 或半宽变化很大，说明结论押在这一道题上。
一道题就能翻结论的话，那个结论本来就不该信。

用法：python tools/case_outliers.py <run_id> [--seat Product]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from variance_decomp import Z95, load_cells  # noqa: E402


def per_case_delta(cells, champ: str, base: str) -> dict[str, list[float]]:
    """题 → [冠军各次均值, 基线各次均值, 分差]"""
    out = {}
    for (arm, case), vals in cells.items():
        if arm != champ:
            continue
        b = cells.get((base, case))
        if not b:
            continue
        out[case] = [st.fmean(vals), st.fmean(b), st.fmean(vals) - st.fmean(b)]
    return out


def ci_halfwidth(deltas: list[float]) -> float:
    """配对分差的正态近似半宽。留一法只需要相对比较，不必上自助。"""
    n = len(deltas)
    if n < 2:
        return float("nan")
    return Z95 * st.stdev(deltas) / math.sqrt(n)


def checks_of(run_id: str, case_id: str) -> list[dict]:
    state = json.loads((ROOT / "data" / "runs" / run_id / "state.json").read_text(encoding="utf-8"))
    for c in state.get("cases") or []:
        if c.get("id") == case_id:
            return c.get("checks") or []
    return []


def describe_checks(checks: list[dict]) -> str:
    if not checks:
        return "无断言"
    tot = sum(float(c.get("weight") or 0) for c in checks) or 1.0
    by: dict[str, float] = {}
    for c in checks:
        by[str(c.get("type"))] = by.get(str(c.get("type")), 0.0) + float(c.get("weight") or 0)
    parts = [f"{k} {v / tot:.0%}" for k, v in sorted(by.items(), key=lambda x: -x[1])]
    return f"{len(checks)} 条断言｜" + "、".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="逐题看分差，找撑起结论的那道题")
    ap.add_argument("run_id")
    ap.add_argument("--seat", default="")
    args = ap.parse_args()

    cells, champ, base, origin, detail = load_cells(args.run_id, "medium_02")
    pc = per_case_delta(cells, champ, base)
    deltas = [v[2] for v in pc.values()]
    full_d, full_hw = st.fmean(deltas), ci_halfwidth(deltas)

    title = f"{args.seat} " if args.seat else ""
    print(f"{title}run {args.run_id}｜{len(pc)} 题｜逐次分数来源：{detail}")
    print(f"全量：Δ={full_d:+.2f}  半宽={full_hw:.2f}  区间={'跨 0' if full_hw > abs(full_d) else '不跨 0'}\n")

    print("  题号                        冠军    基线    分差     去掉它之后 Δ / 半宽")
    for case, (c, b, d) in sorted(pc.items(), key=lambda x: -abs(x[1][2])):
        rest = [v[2] for k, v in pc.items() if k != case]
        r_d, r_hw = (st.fmean(rest), ci_halfwidth(rest)) if len(rest) >= 2 else (float("nan"),) * 2
        flip = ""
        if not math.isnan(r_d):
            if (r_d >= 0) != (full_d >= 0):
                flip = "  ← **去掉它 Δ 换符号**"
            elif abs(r_d) > r_hw and abs(full_d) <= full_hw:
                flip = "  ← **去掉它就判得出了**"
        print(f"  {case:<26} {c:6.1f}  {b:6.1f}  {d:+7.2f}   Δ={r_d:+6.2f} 半宽={r_hw:5.2f}{flip}")

    # 最极端的那道题，把断言构成打出来：结论押在它身上，就得看清它是什么题
    worst = max(pc.items(), key=lambda x: abs(x[1][2]))
    print(f"\n分差最大的一题 {worst[0]}（{worst[1][2]:+.2f}）：{describe_checks(checks_of(args.run_id, worst[0]))}")
    share = worst[1][2] / (sum(deltas) or 1)
    print(f"它单独贡献了全量 Δ 的 {share:.0%}（{len(pc)} 题里的 1 题）")
    print("\n注：留一法是**诊断**不是清洗手段 —— 发现某题撑起结论，该做的是查它有没有毛病，"
          "\n而不是把它删掉让区间变好看。删掉不合意的题就不叫 holdout 了。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
