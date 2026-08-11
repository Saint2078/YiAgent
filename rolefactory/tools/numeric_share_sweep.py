#!/usr/bin/env python3
"""numeric 权重该放多少：**分辨率**与**方差**是同一个旋钮的两头。

§13 把 numeric 权重抬到 60%，买的是分辨率（堆词地板 67.6 → 37.5）。
现在量出代价：numeric 是**逐题分差方差的主项** ——
Product 占 72%、DevOps **97%**、Architect 70%，去掉它 sd 掉 41%~81%。

原因是结构性的：numeric 是**二值**判定（算对给满、算错给零），
权重 60% 意味着单题分差只能是 0 或 ±60。二值 × 大权重 = 天生大方差。

于是"抬权重"同时抬了 Δ（真信号，§15 已量）和 sd（噪声）。
**判定力只认 Δ/sd 的比值**，所以最优权重不是 0 也不是 1，而是让
所需题量 n = (1.96·sd/Δ)² 最小的那个点 —— 这个点可以从盘上数据直接算，0 额度。

一条必须同时看的约束：权重降下去，堆词假答案的地板会**升回来**（§13 那把刀就白挥了）。
所以本工具同时报 gameability，别只优化一头。

用法：python tools/numeric_share_sweep.py [--gameability]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

RUNS = ROOT / "data" / "runs"
SEATS = [
    ("Product", "20260809-191310-a7b2bd"), ("PM", "20260810-185143-6ea6f5"),
    ("Architect", "20260809-194427-8cfdb4"), ("Dev", "20260809-201229-aa45e1"),
    ("DevOps", "20260809-203635-e70531"), ("Evals", "20260810-181341-bbaec2"),
]
SHARES = [0.0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90]
CURRENT = 0.60
Z = 1.96


def load(run_id: str) -> tuple[list[dict], set[str]]:
    names: set[str] = set()
    rep = RUNS / run_id / "report.json"
    if rep.is_file():
        hold = (json.loads(rep.read_text(encoding="utf-8")).get("scores") or {}).get("holdout") or {}
        names = {str(c) for c in (hold.get("cases") or [])}
    rows: list[dict] = []
    for d in (RUNS / f"{run_id}-reholdout", RUNS / run_id):
        p = d / "results.jsonl"
        if not p.is_file():
            continue
        cand = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(cand) > len(rows):
            rows = cand
    return rows, names


def split_frac(row: dict) -> tuple[float | None, float | None]:
    """把一次评测拆成 (numeric 得分率, 其余得分率)，都在 0..1。

    这样任意 numeric 权重 w 下的总分就是 100·(w·num + (1−w)·other) —— 精确，不是近似。
    """
    checks = row.get("checks") or []
    nw = ns = ow = os_ = 0.0
    for c in checks:
        w = float(c.get("weight") or 0)
        s = float(c.get("score") or 0)
        if str(c.get("type")) == "numeric":
            nw += w
            ns += w * s
        else:
            ow += w
            os_ += w * s
    return (ns / nw if nw > 0 else None), (os_ / ow if ow > 0 else None)


def score_at(row: dict, w: float) -> float | None:
    num, oth = split_frac(row)
    if num is None and oth is None:
        return None
    if num is None:
        return 100.0 * (oth or 0.0)
    if oth is None:
        return 100.0 * num
    return 100.0 * (w * num + (1.0 - w) * oth)


def analyse(run_id: str) -> dict[float, tuple[float, float, int]]:
    """→ {numeric份额: (Δ均值, **reps=1 口径的 sd**, 题数)}

    单位必须说清楚，否则会和 `alloc.py` 对不上（我第一版就对不上）：
    这里的逐题 Δ 是 **3 次重复的均值之差**，它的 sd 已经被平均削掉了一部分测量噪声。
    而 holdout 实跑是 **reps=1**，噪声是满的。直接拿前者规划题量会**低估**所需 n ——
    第一版算出 Architect 只需 14 道，而 alloc.py 说 96 道，差 7 倍就是这么来的。

    按分解还原：sd_obs(r)² = 2σ_w²/r + σ_h²，于是
        sd(1)² = sd_obs(r)² + 2σ_w²(1 − 1/r)
    σ_w 用同一批数据的格内方差估（同题同臂重复之间的抖动），随权重一起重算。
    """
    rows, names = load(run_id)
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        case = str(r.get("case") or "")
        if names and case not in names:
            continue
        cells[(str(r.get("variant")), case)].append(r)
    arms = {a for a, _ in cells}
    champs = [a for a in arms if a != "baseline"]
    if "baseline" not in arms or len(champs) != 1:
        return {}
    champ = champs[0]
    cases = sorted({c for a, c in cells if a == champ and ("baseline", c) in cells})

    out: dict[float, tuple[float, float, int]] = {}
    for w in SHARES:
        deltas: list[float] = []
        within: list[float] = []   # 格内方差 → σ_w²
        reps_min = 99
        for c in cases:
            cv = [s for r in cells[(champ, c)] if (s := score_at(r, w)) is not None]
            bv = [s for r in cells[("baseline", c)] if (s := score_at(r, w)) is not None]
            if not cv or not bv:
                continue
            deltas.append(st.fmean(cv) - st.fmean(bv))
            for vals in (cv, bv):
                if len(vals) >= 2:
                    within.append(st.variance(vals))
                    reps_min = min(reps_min, len(vals))
        if len(deltas) < 2:
            continue
        sd_obs = st.stdev(deltas)
        r = reps_min if reps_min < 99 else 1
        if within and r > 1:
            var_w = st.fmean(within)
            # 还原到 reps=1：把平均削掉的那部分噪声加回去
            sd1 = math.sqrt(max(sd_obs**2 + 2 * var_w * (1 - 1 / r), 0.0))
        else:
            sd1 = sd_obs
        out[w] = (st.fmean(deltas), sd1, len(deltas))
    return out


def need_n(delta: float, sd: float) -> float:
    if abs(delta) < 1e-9:
        return float("inf")
    return (Z * sd / abs(delta)) ** 2


def soup_floor(share: float) -> float | None:
    """堆词假答案在该权重下能拿多少分（越低越好）。调 gameability.py，口径不另立一份。"""
    r = subprocess.run(
        [sys.executable, str(HERE / "gameability.py"), "--target-numeric", f"{share}"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        return None
    best: float | None = None
    for ln in (r.stdout or "").splitlines():
        if "soup" in ln.lower():
            for tok in ln.replace("|", " ").split():
                try:
                    v = float(tok)
                except ValueError:
                    continue
                if 0.0 <= v <= 100.0:
                    best = v if best is None else max(best, v)
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="扫 numeric 权重对判定力的影响")
    ap.add_argument("--gameability", action="store_true", help="同时算堆词地板（较慢）")
    args = ap.parse_args()

    print("所需题量 n = (1.96·sd/Δ)² —— 越小越容易判出。当前 numeric 权重 = 60%\n")
    per_seat: dict[str, dict[float, tuple[float, float, int]]] = {}
    for seat, rid in SEATS:
        d = analyse(rid)
        if d:
            per_seat[seat] = d

    hdr = f"{'numeric份额':>10}" + "".join(f"{s:>13}" for s in per_seat)
    print(hdr)
    print("-" * len(hdr))
    for w in SHARES:
        cells = []
        for seat in per_seat:
            v = per_seat[seat].get(w)
            if not v:
                cells.append(f"{'—':>13}")
                continue
            m, sd, _ = v
            n = need_n(m, sd)
            sign = "+" if m >= 0 else "−"
            cells.append(f"{sign}{abs(m):.1f}/n={n:.0f}".rjust(13) if n <= 9999
                         else f"{sign}{abs(m):.1f}/n>1e4".rjust(13))
        mark = " ←现行" if abs(w - CURRENT) < 1e-9 else ""
        print(f"{w * 100:>9.0f}%" + "".join(cells) + mark)

    print("\n（格式：Δ均值 / 所需题量。Δ 变号说明那个权重下结论方向都变了 —— 慎读）")

    # 逐席最优点：n 最小的那个份额
    print("\n逐席最优 numeric 份额（只看判定力，不看可玩性）：")
    better: list[str] = []
    for seat, d in per_seat.items():
        rows = [(w, need_n(*v[:2])) for w, v in sorted(d.items())]
        rows = [(w, n) for w, n in rows if math.isfinite(n)]
        if not rows:
            continue
        w_best, n_best = min(rows, key=lambda t: t[1])
        n_cur = need_n(*d[CURRENT][:2]) if CURRENT in d else float("inf")
        gain = (n_cur / n_best) if n_best > 0 and math.isfinite(n_cur) else float("inf")
        tag = ""
        if n_best <= 90 < n_cur:
            tag = "  ← **现行判不出、这个份额能判出**"
            better.append(seat)
        print(f"  {seat:<12} 最优 {w_best * 100:>3.0f}%：n={n_best:>5.0f}"
              f"（现行 60% 需 n={n_cur:.0f}，省 {gain:.1f}×）{tag}")

    if args.gameability:
        print("\n堆词地板（越低越好；§13 把它从 67.6 压到 37.5 就是靠抬 numeric 权重）：")
        for w in (0.30, 0.45, 0.60):
            f = soup_floor(w)
            print(f"  numeric {w * 100:.0f}% → 堆词得分 {f if f is not None else '算不出'}")

    print("\n判读纪律：")
    print("  · 这是**同一个旋钮的两头**：权重降 → sd 降（好）、Δ 也降（坏）、堆词地板升（坏）。")
    print("    只优化 n 会把尺子的分辨率还回去，§13 那把刀就白挥了。")
    print("  · 与 ceiling_sweep 同理：**不得**扫一圈挑「刚好显著」的份额。")
    print("    份额要按先验口径定（要多少分辨率），再看它够不够判 —— 而不是反过来。")
    if better:
        print(f"  · 但有一条实打实的信息：{'、'.join(better)} 在现行 60% 下判不出、")
        print("    在更低份额下能判出。这说明「四席够不着」部分是**权重选择的后果**，")
        print("    不是能力差异本身太小 —— 值得把它当一个待定的取舍交出去，而不是当结论。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
