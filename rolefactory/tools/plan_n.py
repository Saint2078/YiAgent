#!/usr/bin/env python3
"""新配法够不够：**用去偏之后的 sd 反算需要多少道 holdout**。

§18.9 有一个顺带冒出来的坏消息我差点放过去：扔掉天花板题之后，剩下题的
sd = **20.03**（全体 16.31）—— 门槛把低方差的题拿走了，sd 反而变大。
而新配法（`per_dim=16 / train_per_dim=1`）给出的 holdout 是 42–90 道。

于是必须回答：**42 道够吗？** 半宽 = 1.96·sd/√n，要能判定得满足 半宽 < |Δ|：

    n > (1.96 · sd / Δ)²

这件事必须在花额度**之前**算 —— 否则就是花 550 次调用去买一个注定"判不了"。

一条诚实标注：这里的 Δ 用的是"扔掉天花板题之后"的估计（v3 试跑 +5.78）。
它本身来自筛过的样本，**乐观偏差在所难免**（选出来的题正好是显得有效的那批）。
所以下面同时报几个更保守的 Δ，看结论在多大范围内稳。

用法：python tools/plan_n.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import ceiling_sweep as cs  # noqa: E402

# 新配法（build_devteam.RUN_PARAMS）：6 维 × per_dim，train 每维 1 道，其余全进 holdout
PER_DIM = 16
DIMS = 6
TRAIN_PER_DIM = 1
CEILING = 90.0


def need_n(delta: float, sd: float, z: float = 1.96) -> float:
    if delta <= 0:
        return float("inf")
    return (z * sd / delta) ** 2


def main() -> int:
    # 1) 拿去偏之后的 sd：各席"非天花板题"的逐题 Δ 合起来
    lo_all: list[float] = []
    per_seat: list[tuple[str, int, float, float]] = []
    for seat, rid in cs.SEATS:
        rows, _ = cs._load_rows(rid)
        if not rows:
            continue
        pc = cs.per_case(rows)
        lo = [v["delta"] for v in pc.values() if v["base"] <= CEILING]
        if len(lo) < 2:
            continue
        import statistics as st

        lo_all += lo
        per_seat.append((seat, len(lo), st.fmean(lo), st.stdev(lo)))

    import statistics as st

    sd_pool = st.stdev(lo_all)
    m_pool = st.fmean(lo_all)

    print(f"去偏后的逐题 Δ（门槛 {CEILING:g}，{len(lo_all)} 道题合池）：")
    print(f"  均值 {m_pool:+.2f}、sd {sd_pool:.2f}\n")
    print("  逐席（非天花板题）：")
    for seat, n, m, sd in per_seat:
        print(f"    {seat:<14} n={n:<3} Δ={m:>+6.2f}  sd={sd:>6.2f}")

    # 2) 新配法能给多少 holdout
    total = PER_DIM * DIMS
    train = TRAIN_PER_DIM * DIMS
    hold_max = total - train                      # 一道都没扔
    hold_min = hold_max - int(PER_DIM * 0.5) * DIMS  # 每维扔满一半
    print(f"\n新配法 per_dim={PER_DIM} × {DIMS} 维 = {total} 道，train 封顶 {train} 道")
    print(f"  → holdout 区间 **{max(hold_min, 0)}–{hold_max} 道**（扔满 / 一道不扔）")

    # 3) 反算：要判得出，需要多少道
    print(f"\n用 sd={sd_pool:.2f} 反算「要判得出需要多少道 holdout」：\n")
    print("   假定真实 Δ    需要 n     42 道够吗   90 道够吗")
    verdicts: list[tuple[float, bool, bool]] = []
    for d in (8.0, 5.78, 5.0, 3.0, 2.0, 1.41):
        n = need_n(d, sd_pool)
        ok42, ok90 = n <= 42, n <= hold_max
        verdicts.append((d, ok42, ok90))
        tag42 = "✓" if ok42 else "✗"
        tag90 = "✓" if ok90 else "✗"
        note = ""
        if abs(d - 5.78) < 0.01:
            note = "  ← v3 试跑去偏后的实测点估计"
        if abs(d - 1.41) < 0.01:
            note = "  ← PM 原始效应量（§10）"
        print(f"   {d:>+8.2f}     {n:>7.0f}      {tag42:^8}   {tag90:^8}{note}")

    print("\n判读：")
    ok42_at_578 = need_n(5.78, sd_pool) <= 42
    ok90_at_578 = need_n(5.78, sd_pool) <= hold_max
    if ok42_at_578:
        print(f"  · 若去偏后的真实效应确有 +5.78，42 道就够（需 {need_n(5.78, sd_pool):.0f} 道）。")
    elif ok90_at_578:
        print(f"  · 若真实效应 +5.78，**42 道不够**（需 {need_n(5.78, sd_pool):.0f} 道），"
              f"但扔得少、holdout 接近 {hold_max} 道时够。")
        print("    也就是说：**这次能不能判，取决于门槛实际扔掉多少题** ——")
        print("    扔得多反而更判不出。这条和「门槛能提高判定力」是相反的，与 §18.9 一致。")
    else:
        print(f"  · 即便 holdout 拉到 {hold_max} 道，+5.78 也判不出（需 {need_n(5.78, sd_pool):.0f} 道）。")
        print("    **新配法仍然不够** —— 花额度之前就该知道这件事。")

    n_small = need_n(2.0, sd_pool)
    print(f"  · 若真实效应只有 +2，需要 **{n_small:.0f} 道** —— 远超新配法上限 {hold_max}。")
    print("    这类小效应在当前尺子下**不可能判定**，除非先把 sd 压下来（降噪 > 加题）。")
    print("\n标注（诚实边界）：")
    print("  · Δ=+5.78 来自「筛过之后」的样本，**乐观偏差在所难免**（选中的正是显得有效的那批），")
    print("    只能当上界看。真跑出来大概率比它小。")
    print("  · sd=20.03 也是筛后的值：门槛拿走了低方差题，sd 因此比全体（16.31）更大。")
    print("  · 两个数一起用，方向相反：Δ 偏乐观让 n 偏小，sd 偏大让 n 偏大。净效应不定。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
