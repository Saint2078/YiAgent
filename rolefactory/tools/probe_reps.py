#!/usr/bin/env python3
"""查每个 run 的逐条明细里，同一题同一臂到底存了几次分数。

问的是一件很具体的事：**方差分解能不能就地做**。分解要求同题同臂 reps≥2，
而复核是 reps=3 跑的 —— 如果复核把逐次分数追加进了 results.jsonl，
那就不用等额度，现在就能把「测量噪声」和「题间差异」拆开。

用法：python tools/probe_reps.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "data" / "runs"


def main() -> int:
    print("run                       holdout题  有明细  同题同臂最多几次  可分解")
    for d in sorted(RUNS.iterdir()):
        if not d.is_dir():
            continue
        rep = d / "report.json"
        if not rep.is_file():
            continue
        report = json.loads(rep.read_text(encoding="utf-8"))
        hold = (report.get("scores") or {}).get("holdout") or {}
        names = set(str(c) for c in (hold.get("cases") or []))
        rl = d / "results.jsonl"
        if not rl.is_file():
            print(f"{d.name:24}  {len(names):>6}   无明细    —                 否")
            continue

        cells: dict[tuple[str, str], int] = defaultdict(int)
        for line in rl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            c = str(r.get("case") or "")
            if names and c not in names:
                continue
            cells[(str(r.get("variant")), c)] += 1
        counts = Counter(cells.values())
        mx = max(counts) if counts else 0
        ok = "**可以**" if mx >= 2 else "否（只存了 1 次）"
        print(f"{d.name:24}  {len(names):>6}   有        {mx:<17} {ok}")
        if counts:
            print(f"{'':24}  次数分布 {dict(sorted(counts.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
