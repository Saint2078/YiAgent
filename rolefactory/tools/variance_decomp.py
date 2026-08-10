#!/usr/bin/env python3
"""方差分解：holdout 判不了，到底该**加重复**还是**加题**。

两种噪声混在一起，处方完全相反：

- **每题内部的测量噪声** σ²_w（同一题同一臂重复几次，分数还会抖）→ 加 `reps` 能压
- **题与题之间的真实差异** σ²_b（基因在 A 题有用、在 B 题没用）→ 只能加题

分不清就会一直加重复、一直判不了。好在 `reps≥2` 的 run 里 `results.jsonl` 存了
逐次分数，**不用再花额度重跑**就能把两者拆开：

    每题分差方差  Var(d) = σ²_b + 2σ²_w / reps        （两臂各自平均，故 2×）
    区间半宽      HW(n, r) = 1.96 · √(σ²_b + 2σ²_w/r) / √n

关键量是 **r→∞ 时的半宽下限** `1.96·σ_b/√n`：重复次数再多也降不到它以下。
下限已经大于实测分差，就说明加重复无用，必须加题。

哪些题算 holdout，**以 `report.json` 的 `scores.holdout.cases` 为准**。别按题号猜：
早期 holdout 恰好是每维一道 `medium_02`，按后缀筛能对上；`holdout_per_dim` 一开大，
后缀就只能捞到其中一小撮，还会混进 train 题 —— 实测捞到 6 道 train 题、算出个
完全无关的 Δ 且不报错（见 PERF.md §16）。

用法：
    python tools/variance_decomp.py <run_id> [--holdout-suffix medium_02]
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"
Z95 = 1.959964


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _var(xs: list[float]) -> float | None:
    """样本方差（n−1）。少于 2 个点则无法估计。"""
    if len(xs) < 2:
        return None
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def holdout_cases(run_id: str, suffix: str) -> tuple[set[str], str]:
    """该 run 的 holdout 题号集合。优先取报告里记下的那一份。"""
    rep = RUNS / run_id / "report.json"
    if rep.is_file():
        hold = (json.loads(rep.read_text(encoding="utf-8")).get("scores") or {}).get("holdout") or {}
        names = [str(c) for c in (hold.get("cases") or [])]
        if names:
            return set(names), "report.json"
    return set(), f"后缀 {suffix!r}（报告里没记 holdout 题号，退回猜）"


def load_cells(
    run_id: str, suffix: str
) -> tuple[dict[tuple[str, str], list[float]], str, str, str]:
    """读逐条明细，聚成 (臂, 题) → 各次重复的分数。返回冠军臂、基线臂与题号来源。"""
    p = RUNS / run_id / "results.jsonl"
    if not p.is_file():
        raise SystemExit(
            f"缺逐条明细 {p}（results.jsonl 是运行时产物、未入库）。"
            "只有在跑过该 run 的机器上才能做分解。"
        )
    names, origin = holdout_cases(run_id, suffix)
    keep = (lambda c: c in names) if names else (lambda c: suffix in c)

    cells: dict[tuple[str, str], list[float]] = defaultdict(list)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        case = str(r.get("case") or "")
        if not keep(case):
            continue
        score = r.get("score")
        if isinstance(score, (int, float)):
            cells[(str(r.get("variant")), case)].append(float(score))

    arms = {a for a, _ in cells}
    if "baseline" not in arms or len(arms) != 2:
        raise SystemExit(
            f"holdout 臂不是「基线 + 冠军」两条：{sorted(arms)}（题号来源：{origin}）"
        )
    champ = next(a for a in arms if a != "baseline")
    return cells, champ, "baseline", origin


def decompose(cells: dict[tuple[str, str], list[float]], champ: str, base: str) -> dict[str, Any]:
    cases = sorted({c for _, c in cells})
    reps = min(len(v) for v in cells.values())

    # 每格（臂×题）内部方差 → 合并成测量噪声估计
    within = [v for cell in cells.values() if (v := _var(cell)) is not None]
    var_w = _mean(within) if within else None

    deltas = []
    for case in cases:
        cv, bv = cells.get((champ, case)), cells.get((base, case))
        if cv and bv:
            deltas.append(_mean(cv) - _mean(bv))
    var_d = _var(deltas)

    out: dict[str, Any] = {
        "cases": len(cases),
        "reps": reps,
        "mean_delta": round(_mean(deltas), 2) if deltas else None,
        "var_within": round(var_w, 2) if var_w is not None else None,
        "sd_within": round(math.sqrt(var_w), 2) if var_w else None,
        "var_delta_observed": round(var_d, 2) if var_d is not None else None,
        "sd_delta_observed": round(math.sqrt(var_d), 2) if var_d else None,
    }
    if var_w is None or var_d is None:
        return out

    # 题间方差 = 观测到的分差方差 − 测量噪声贡献。可能算成负数：
    # 那不代表「负方差」，而是「题间差异小到被抽样误差盖住」，按 0 处理并说明。
    var_b_raw = var_d - 2 * var_w / reps
    out["var_between_raw"] = round(var_b_raw, 2)
    var_b = max(0.0, var_b_raw)
    out["var_between"] = round(var_b, 2)
    out["sd_between"] = round(math.sqrt(var_b), 2)
    out["between_share"] = round(var_b / var_d, 2) if var_d > 0 else None
    return out


def half_width(var_b: float, var_w: float, n: int, r: int) -> float:
    return Z95 * math.sqrt(var_b + 2 * var_w / r) / math.sqrt(n)


def report(run_id: str, d: dict[str, Any], origin: str = "report.json") -> None:
    n, r = d["cases"], d["reps"]
    print(f"run {run_id} · holdout {n} 题 × {r} 次重复 · 实测 Δ={d['mean_delta']}")
    print(f"  （holdout 题号来源：{origin}）")
    if d.get("var_between") is None:
        print(
            "  数据不足，分解不了：拆开测量噪声要求**同一题同一臂至少跑 2 次**，"
            f"这个 run 是 reps={r}。\n"
            "  想分解就在同批题上复核一次：POST /api/run/{run_id}/reholdout {\"reps\":3}"
        )
        return

    var_b, var_w = d["var_between"], d["var_within"]
    print(f"\n  每题分差 sd（实测）      {d['sd_delta_observed']}")
    print(f"  每题内部测量噪声 sd      {d['sd_within']}   ← 加 reps 能压这一项")
    print(f"  题与题之间差异 sd        {d['sd_between']}   ← 只有加题能压这一项")
    if d["var_between_raw"] < 0:
        print(
            f"  （题间方差原始估计 {d['var_between_raw']} 为负 → 按 0 处理："
            "不是真的负方差，而是题间差异小到被抽样误差盖住）"
        )
    elif d.get("between_share") is not None:
        print(f"  题间差异占比            {d['between_share']:.0%}")

    delta = abs(d["mean_delta"] or 0)
    floor = Z95 * math.sqrt(var_b) / math.sqrt(n) if var_b > 0 else 0.0
    print(f"\n  当前 {n} 题 {r} 次重复的区间半宽   {half_width(var_b, var_w, n, r):.2f}")
    print(f"  同样 {n} 题、重复次数 →∞ 的下限    {floor:.2f}")
    if delta:
        if floor >= delta:
            print(
                f"  → **加重复救不了**：{n} 题的半宽下限 {floor:.2f} ≥ |Δ|={delta:.2f}，"
                "无论重复多少次都判不了，只能加题。"
            )
        else:
            need_r = None
            for rr in range(r, 201):
                if half_width(var_b, var_w, n, rr) < delta:
                    need_r = rr
                    break
            print(
                f"  → 加重复**有可能**够：{n} 题不变，重复到 {need_r} 次半宽可降到 |Δ| 以下。"
                if need_r
                else "  → 200 次以内不够，仍需加题。"
            )

    if not delta:
        return
    print("\n  设计表：达到「半宽 < |Δ|」的几种配法（评测数 = 2 臂 × 题数 × 重复）")
    print("  | reps | 所需题数 | holdout 评测数 |")
    print("  |------|----------|----------------|")
    plans = []
    for rr in (1, 2, 3, 5, 10, 30):
        need_n = math.ceil((Z95 / delta) ** 2 * (var_b + 2 * var_w / rr))
        evals = 2 * need_n * rr
        plans.append((evals, rr, need_n))
        print(f"  | {rr:4} | {need_n:8} | {evals:14} |")
    cheap = min(plans)
    print(
        f"\n  最省的一档是 reps={cheap[1]} × {cheap[2]} 题（{cheap[0]} 次评测）："
        "\n  题多重复少比题少重复多便宜 —— 重复只压 1/r，题数是线性压，而两者单价一样。"
        f"\n  另一面：题得先出得出来。现有 holdout 只有 {n} 题，凑到 {cheap[2]} 题要先扩题库。"
    )
    print(
        "\n  注：表按「实测 Δ 就是真实效应」算。真实效应更小则所需题数按平方放大；"
        f"\n  且 σ 只由 {n} 题估出，自身误差不小 —— 当量级参考，别当精确值。"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="holdout 方差分解：该加重复还是加题")
    ap.add_argument("run_id")
    ap.add_argument("--holdout-suffix", default="medium_02", help="holdout 题 id 的标识子串")
    args = ap.parse_args()
    cells, champ, base, origin = load_cells(args.run_id, args.holdout_suffix)
    report(args.run_id, decompose(cells, champ, base), origin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
