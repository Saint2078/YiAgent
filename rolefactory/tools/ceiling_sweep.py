#!/usr/bin/env python3
"""扫门槛：**去掉天花板题，区间到底会变窄还是变宽？**

筛题门槛（PERF.md §18.6–18.7）整套是建在一个**假设**上的：基线贴满分的题量不出提升，
扔掉它们能提高判定力。前半句已量实（`headroom.py`：27% 的题留不下 5 分空间），
但后半句**一直没验**。而它完全可能是反的 ——

半宽 ≈ t · sd(逐题Δ) / √n。扔题同时动了分子和分母：
  · 若天花板题的 Δ 接近 0 **且方差很小**，它们其实在**压低** sd。扔掉 → sd 变大、
    n 变小，**两头都往坏的方向走**，门槛反而降低判定力。
  · 只有当它们的 Δ 方差不低于其余题时，扔掉才是净赚。

哪种为真只能看数据。本工具把门槛从 100 扫到 70，逐档报 n / 均值Δ / sd / 半宽 / 判定，
0 额度（只读盘上的 `results.jsonl`）。

用法：python tools/ceiling_sweep.py [--md]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "data" / "runs"
SEATS = [
    ("Product", "20260809-191310-a7b2bd"), ("PM", "20260810-185143-6ea6f5"),
    ("Architect", "20260809-194427-8cfdb4"), ("Dev", "20260809-201229-aa45e1"),
    ("DevOps", "20260809-203635-e70531"), ("Evals", "20260810-181341-bbaec2"),
    ("v3试跑(41题)", "20260810-213118-209063"),
]
CEILINGS = [100.0, 98.0, 95.0, 92.0, 90.0, 85.0, 80.0, 75.0, 70.0]


def _load_rows(run_id: str) -> tuple[list[dict], set[str]]:
    """取 holdout 逐条明细。reps≥2 的复核落在 `<run>-reholdout/`，优先用它。"""
    rep_p = RUNS / run_id / "report.json"
    if not rep_p.is_file():
        return [], set()
    report = json.loads(rep_p.read_text(encoding="utf-8"))
    hold = (report.get("scores") or {}).get("holdout") or {}
    names = {str(c) for c in (hold.get("cases") or [])}

    best: list[dict] = []
    for d in (RUNS / f"{run_id}-reholdout", RUNS / run_id):
        p = d / "results.jsonl"
        if not p.is_file():
            continue
        rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        rows = [r for r in rows if not names or str(r.get("case")) in names]
        # 选重复数更多的那份
        cells: dict[tuple, int] = defaultdict(int)
        for r in rows:
            cells[(str(r.get("variant")), str(r.get("case")))] += 1
        if rows and (not best or max(cells.values(), default=0) > _max_reps(best)):
            best = rows
    return best, names


def _max_reps(rows: list[dict]) -> int:
    cells: dict[tuple, int] = defaultdict(int)
    for r in rows:
        cells[(str(r.get("variant")), str(r.get("case")))] += 1
    return max(cells.values(), default=0)


def per_case(rows: list[dict]) -> dict[str, dict[str, float]]:
    """逐题：基线均分、冠军均分、Δ。两个臂按 variant 名里的 baseline 区分。"""
    by: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        s = r.get("score")
        if isinstance(s, (int, float)):
            arm = "base" if "baseline" in str(r.get("variant")).lower() else "champ"
            by[(arm, str(r.get("case")))].append(float(s))
    cases = {c for _, c in by}
    out: dict[str, dict[str, float]] = {}
    for c in cases:
        b, ch = by.get(("base", c)) or [], by.get(("champ", c)) or []
        if not b or not ch:
            continue
        out[c] = {"base": st.fmean(b), "champ": st.fmean(ch),
                  "delta": st.fmean(ch) - st.fmean(b)}
    return out


def stats(deltas: list[float]) -> tuple[float, float, float]:
    n = len(deltas)
    if n < 2:
        return (st.fmean(deltas) if deltas else 0.0), 0.0, float("inf")
    m, sd = st.fmean(deltas), st.stdev(deltas)
    return m, sd, 1.96 * sd / math.sqrt(n)


def main() -> int:
    ap = argparse.ArgumentParser(description="扫筛题门槛对判定力的实际影响")
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    rows_out: list[dict[str, Any]] = []
    for seat, rid in SEATS:
        rows, _ = _load_rows(rid)
        if not rows:
            continue
        pc = per_case(rows)
        if len(pc) < 3:
            continue
        base_all = [v["delta"] for v in pc.values()]
        m0, sd0, hw0 = stats(base_all)
        for C in CEILINGS:
            kept = [v["delta"] for v in pc.values() if v["base"] <= C]
            if len(kept) < 2:
                continue
            m, sd, hw = stats(kept)
            rows_out.append({
                "seat": seat, "ceiling": C, "n": len(kept), "n_all": len(pc),
                "mean": m, "sd": sd, "hw": hw,
                "decisive": hw < abs(m) and len(kept) >= 2,
                "hw_base": hw0, "mean_base": m0,
            })

    if not rows_out:
        print("没有可用的逐条明细")
        return 1

    for seat in dict.fromkeys(r["seat"] for r in rows_out):
        rs = [r for r in rows_out if r["seat"] == seat]
        n_all = rs[0]["n_all"]
        print(f"\n{seat}（holdout {n_all} 题，含明细）")
        print("  门槛   留题  均值Δ    sd     半宽    判定    与不筛相比")
        for r in rs:
            base_hw = r["hw_base"]
            if r["ceiling"] >= 100:
                cmp = "（基准）"
            else:
                d = r["hw"] - base_hw
                cmp = f"半宽{'+' if d >= 0 else ''}{d:.2f}" + ("  ← 更差" if d > 0.01 else
                                                              "  ← 更好" if d < -0.01 else "")
            print(f"  {r['ceiling']:>5.0f}  {r['n']:>4}  {r['mean']:>+6.2f}  "
                  f"{r['sd']:>5.2f}  {r['hw']:>6.2f}   "
                  f"{'**判得出**' if r['decisive'] else '判不了':<8} {cmp}")

    # 总账：门槛 90 相对不筛，究竟改善了几席
    print("\n" + "=" * 74)
    better = worse = same = 0
    for seat in dict.fromkeys(r["seat"] for r in rows_out):
        rs = {r["ceiling"]: r for r in rows_out if r["seat"] == seat}
        if 90.0 not in rs or 100.0 not in rs:
            continue
        d = rs[90.0]["hw"] - rs[100.0]["hw"]
        if d < -0.01:
            better += 1
        elif d > 0.01:
            worse += 1
        else:
            same += 1
    print(f"门槛=90 对比不筛：半宽变窄 {better} 席、变宽 {worse} 席、基本不变 {same} 席")
    print("提醒：半宽 ≈ 1.96·sd/√n。扔题同时减小 n（坏）并改变 sd（可好可坏）——")
    print("      若天花板题的 Δ 方差本来就低，扔掉它们会把 sd 抬上去，两头一起变坏。")
    print("      这张表的用途是**证伪**「扔了就一定更准」，不是给门槛背书。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
