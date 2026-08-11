#!/usr/bin/env python3
"""同一笔额度：**多出题**还是**多重复**？把它当约束最优化算，别靠直觉。

§18.9 之后剩下的真问题不是"够不够 42 道"，而是"一笔固定额度怎么花最划算"。
把逐题 Δ 的方差按 §17 的分解写开：

    sd²(逐题Δ) = 2σ_w²/reps + σ_h²

  · σ_w = 单次测量噪声（同题同臂重复之间的抖动）→ **多重复能压**
  · σ_h = 真实效应的题间异质（这题基因确实有用、那题确实没用）→ **重复压不动**

半宽 ≈ 1.96·sd/√n，而额度 B = 2 臂 × n × reps。代入 n = B/(2·reps)：

    半宽² ∝ (2σ_w²/reps + σ_h²) · 2·reps / B = (4σ_w² + 2σ_h²·reps) / B

**reps 只出现在分子里**。于是结论是反直觉但干净的：额度固定时，
σ_h > 0 就该 **reps=1、把钱全花在加题上**；σ_h = 0 时两种花法等价。

这条正好解释了为什么"加题救不了"（§16）和"该加重复"（§17）看着矛盾却都对 ——
它们是 σ_h > 0 与 σ_h ≈ 0 两种席位。

还有一条只有写成公式才看得见的东西：**reps 有地板**。
reps → ∞ 时半宽 → 1.96·σ_h/√n，与 reps 无关。题量不够时，
再多重复也压不到这个地板以下 —— 加重复的席位必须先确认地板在效应量之下。

用法：python tools/alloc.py [--budget 180]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import variance_decomp as vd  # noqa: E402

SEATS = [
    ("Product", "20260809-191310-a7b2bd"), ("PM", "20260810-185143-6ea6f5"),
    ("Architect", "20260809-194427-8cfdb4"), ("Dev", "20260809-201229-aa45e1"),
    ("DevOps", "20260809-203635-e70531"), ("Evals", "20260810-181341-bbaec2"),
]
Z = 1.96


def hw(sig_w: float, sig_h: float, n: int, reps: int) -> float:
    """半宽：z·sd/√n，其中 sd² = 2σ_w²/reps + σ_h²。"""
    if n < 2:
        return float("inf")
    sd2 = 2 * sig_w**2 / max(1, reps) + sig_h**2
    return Z * math.sqrt(sd2) / math.sqrt(n)


def floor_hw(sig_h: float, n: int) -> float:
    """reps→∞ 的地板：重复压不动的那部分。"""
    if n < 2:
        return float("inf")
    return Z * sig_h / math.sqrt(n)


def main() -> int:
    ap = argparse.ArgumentParser(description="固定额度下的 (题量, 重复) 最优分配")
    ap.add_argument("--budget", type=int, default=180, help="一次复核的评测次数上限")
    args = ap.parse_args()
    B = args.budget

    print(f"额度 B = {B} 次评测（= 2 臂 × 题量 × 重复）\n")
    print("逐席：σ_w（可压）/ σ_h（压不动）/ 当前效应，以及同一笔额度的两种花法\n")
    hdr = (f"{'席位':<12}{'σ_w':>7}{'σ_h':>7}{'|Δ|':>7}  "
           f"{'reps=1 加题':>16}{'reps=多 少题':>18}  保本题量  处方")
    print(hdr)
    print("-" * len(hdr))

    skipped: list[str] = []
    for seat, rid in SEATS:
        try:
            cells, champ, base, _origin, _detail = vd.load_cells(rid, "medium_02")
            d = vd.decompose(cells, champ, base)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{seat}（读不到明细：{type(exc).__name__}）")
            continue
        if not d or d.get("var_between") is None:
            # reps=1 的 run 分解不了：σ_w 与 σ_h 拆不开，这里不能拿观测方差硬当 σ_h
            skipped.append(f"{seat}（reps={d.get('reps') if d else '?'}，分解不了）")
            continue
        sig_w = math.sqrt(max(0.0, d.get("var_within") or 0.0))
        sig_h = math.sqrt(max(0.0, d.get("var_between") or 0.0))
        delta = abs(d.get("mean_delta") or 0.0)

        # 花法 A：reps=1，题量拉满
        n_a = B // 2
        hw_a = hw(sig_w, sig_h, n_a, 1)
        # 花法 B：题量维持现状（现有 holdout），重复拉满
        n_b = max(2, int(d.get("cases") or 6))
        reps_b = max(1, B // (2 * n_b))
        hw_b = hw(sig_w, sig_h, n_b, reps_b)

        best = "加题" if hw_a < hw_b else ("加重复" if hw_b < hw_a else "等价")
        dec_a = hw_a < delta if delta > 0 else False
        dec_b = hw_b < delta if delta > 0 else False
        fl = floor_hw(sig_h, n_b)

        note = f"**{best}**"
        if dec_a and not dec_b:
            note += "（只有加题能判出）"
        elif dec_b and not dec_a:
            note += "（只有加重复能判出）"
        elif dec_a and dec_b:
            note += "（两种都能判出）"
        else:
            note += "（两种都判不出）"
        if delta > 0 and fl >= delta:
            note += f" ⚠ 重复地板 {fl:.2f} ≥ |Δ| {delta:.2f}，**加重复注定判不出**"

        # 保本题量：reps=1 时要判得出，至少需要多少道 holdout
        sd1 = math.sqrt(2 * sig_w**2 + sig_h**2)
        n_need = math.ceil((Z * sd1 / delta) ** 2) if delta > 0 else None
        need_s = f"{n_need}" if n_need and n_need <= 400 else ("—" if not n_need else ">400")

        print(f"{seat:<12}{sig_w:>7.2f}{sig_h:>7.2f}{delta:>7.2f}  "
              f"n={n_a:<3} 半宽{hw_a:>6.2f}  n={n_b} reps={reps_b:<2} 半宽{hw_b:>6.2f}  "
              f"需{need_s:>4}道  {note}")

    if skipped:
        print(f"\n（跳过：{'；'.join(skipped)}）")

    print("\n" + "=" * 78)
    print("为什么公式上「加题」几乎总赢（σ_h > 0 时）：")
    print("  半宽² ∝ (4σ_w² + 2σ_h²·reps) / B —— reps 只出现在分子。")
    print("  同一笔钱，重复买的是「同一道题问得更准」，加题买的是「更多独立信息」；")
    print("  σ_h > 0 意味着题与题之间真的不同，那部分只能靠题量摊薄。")
    print()
    print("唯一的例外是 σ_h ≈ 0（该席的题彼此没差别）—— 此时两种花法等价，")
    print("而加重复**不需要新出题、不需要新 run**，所以更省事。这正是 Evals 排 reps=15 的依据。")
    print()
    print("必须同时检查的一条：**重复有地板** 1.96·σ_h/√n，与 reps 无关。")
    print("  地板高于效应量时，reps 加到多少都判不出 —— 上表已逐席标 ⚠。")
    print()
    print("「保本题量」是 reps=1 下判得出所需的最少 holdout 题数。它直接决定新配法够不够：")
    print(f"  新配法（per_dim=16 / train_per_dim=1）给 42–90 道，")
    print("  所以保本题量 ≤ 42 的席位稳判，43–90 的席位**取决于门槛实际扔掉多少**，>90 的免谈。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
