#!/usr/bin/env python3
"""六席 holdout 判定汇总表（离线，读落盘证据，不发请求）。

两个 Δ 都打出来：`delta_weighted` 是按维度权重压成总分再相减，`paired.mean_delta` 是
逐题相减再平均，**置信区间只属于后者**。混着读会把「快显著了」读进一个没有区间的数
（PERF.md §16.2）。holdout 有复核就用复核那份，与基因组卡同口径。

用法：python tools/holdout_table.py [--md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from build_devteam import TEAM  # noqa: E402
from genome_card import effective_holdout  # noqa: E402

WB = ROOT.parent / "console" / "_workbench" / "AgentTeam" / "Develop"


def seat_run(seat: str) -> tuple[str | None, str | None]:
    p = WB / seat / "genome.json"
    if not p.is_file():
        return None, None
    src = (json.loads(p.read_text(encoding="utf-8")).get("source") or {})
    v = src.get("verdict")
    # `verdict` 早期是字符串、现在是 {generalizes,label,reason} —— 两种都读
    label = v.get("label") if isinstance(v, dict) else v
    return src.get("run_id"), label


def main() -> int:
    ap = argparse.ArgumentParser(description="六席 holdout 判定汇总")
    ap.add_argument("--md", action="store_true", help="输出 markdown 表")
    args = ap.parse_args()

    rows = []
    for member in TEAM:
        seat = member["seat"]
        rid, verdict = seat_run(seat)
        if not rid:
            rows.append((seat, "—", "—", "—", "—", "—", "无落盘基因组"))
            continue
        rep_p = ROOT / "data" / "runs" / rid / "report.json"
        if not rep_p.is_file():
            rows.append((seat, rid, "—", "—", "—", "—", "报告不在本机"))
            continue
        report = json.loads(rep_p.read_text(encoding="utf-8"))
        hold, source, _ = effective_holdout(rid, report.get("scores") or {})
        p = hold.get("paired") or {}
        ci = p.get("mean_delta_ci95")
        rows.append((
            seat, rid[:15],
            f"{hold.get('reps') or 1}×{p.get('cases') or len(hold.get('cases') or [])}",
            str(hold.get("delta_weighted")),
            str(p.get("mean_delta")),
            f"[{ci[0]:+}, {ci[1]:+}]" if ci else "无区间",
            (verdict or "?") + ("（复核）" if source == "reholdout" else ""),
        ))

    head = ("席位", "run", "reps×题", "Δ加权", "Δ配对", "配对 95%CI", "判定")
    if args.md:
        print("| " + " | ".join(head) + " |")
        print("|" + "|".join(["---"] * len(head)) + "|")
        for r in rows:
            print("| " + " | ".join(r) + " |")
    else:
        w = [max(len(str(r[i])) for r in [head, *rows]) for i in range(len(head))]
        for r in [head, *rows]:
            print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    print("\n注：置信区间只属于「Δ配对」。「Δ加权」是另一种算法，没有区间，别把区间读到它上面。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
