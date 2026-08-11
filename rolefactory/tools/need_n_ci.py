#!/usr/bin/env python3
"""保本题量本身有多不确定：给 n 做 bootstrap，**别拿点估计当结论**。

这个工具是来查我自己的账的。§18.10 我用 `alloc.py` 算出一张"保本题量"表，
据此下了两个结论并改了配法：

  · 「只有 Evals(53)/PM(55) 够得着，其余四席 96 至 >400 道，当前额度免谈」
  · per_dim 16 → 21

但 `numeric_share_sweep.py` 从**同一批盘上数据**、用另一条路算同一个量，
得到 Architect 14、Dev 10、DevOps 7 —— 与 alloc 的 96 / 167 / >400 差 7 至 60 倍。
两个估计量指向同一个真值却差这么多，说明**至少有一个不可信**，
而它们共同的软肋是显然的：

    n = (1.96·sd/Δ)²

sd 和 Δ 都是从 **5–6 道 holdout 题**估出来的。n 对 sd 是**二次**依赖，
对 Δ 是**负二次**依赖，而 Δ 恰恰是那个"我们还判不出它是否为 0"的量 ——
拿一个判不出符号的数去做分母，再平方，误差会被放大到没有意义。

所以正确的做法不是在两个点估计里挑一个，而是**给 n 加区间**：
对逐题 Δ 做有放回重采样，每次重算 n，看它的分布。
如果 90% 区间横跨 10 到 400，那么"四席够不着"就**不是一个已建立的结论**，
per_dim=21 也不是"反算"出来的 —— 只是一个恰好不坏的选择。

用法：python tools/need_n_ci.py [--boot 4000]
"""
from __future__ import annotations

import argparse
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import ceiling_sweep as cs  # noqa: E402

Z = 1.96


def need_n(deltas: list[float]) -> float:
    if len(deltas) < 2:
        return float("inf")
    m, sd = st.fmean(deltas), st.stdev(deltas)
    if abs(m) < 1e-9:
        return float("inf")
    return (Z * sd / abs(m)) ** 2


def main() -> int:
    ap = argparse.ArgumentParser(description="保本题量的 bootstrap 区间")
    ap.add_argument("--boot", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20260811)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    print("保本题量 n = (1.96·sd/Δ)²，对逐题 Δ 做有放回重采样\n")
    print(f"{'席位':<12}{'题数':>5}{'点估计n':>9}{'中位n':>8}"
          f"{'5%':>8}{'95%':>9}   判读")
    print("-" * 78)

    rows_out = []
    for seat, rid in cs.SEATS:
        rows, _ = cs._load_rows(rid)
        if not rows:
            continue
        pc = cs.per_case(rows)
        deltas = [v["delta"] for v in pc.values()]
        if len(deltas) < 3:
            continue
        point = need_n(deltas)
        boots: list[float] = []
        inf_hits = 0
        for _ in range(args.boot):
            samp = [rng.choice(deltas) for _ in deltas]
            v = need_n(samp)
            if math.isfinite(v):
                boots.append(v)
            else:
                inf_hits += 1
        if not boots:
            continue
        boots.sort()
        med = boots[len(boots) // 2]
        lo = boots[int(0.05 * len(boots))]
        hi = boots[int(0.95 * len(boots))]

        span = hi / max(lo, 1e-9)
        verdict = ""
        if inf_hits > args.boot * 0.05:
            verdict = f"**{inf_hits * 100 // args.boot}% 重采样里 Δ 过零 → n 无上界**"
        elif span > 20:
            verdict = f"区间跨 {span:.0f}× → **点估计无意义**"
        elif span > 5:
            verdict = f"区间跨 {span:.0f}× → 只能当量级看"
        else:
            verdict = "区间较紧，可用"

        def f(v: float) -> str:
            return f"{v:.0f}" if v < 99999 else ">1e5"

        print(f"{seat:<12}{len(deltas):>5}{f(point):>9}{f(med):>8}"
              f"{f(lo):>8}{f(hi):>9}   {verdict}")
        rows_out.append((seat, point, lo, hi, inf_hits / args.boot))

    print("\n判读：")
    wide = [s for s, _, lo, hi, _ in rows_out if hi / max(lo, 1e-9) > 20]
    crossing = [s for s, _, _, _, fr in rows_out if fr > 0.05]
    if wide:
        print(f"  · {'、'.join(wide)}：n 的 90% 区间跨了 20 倍以上。")
        print("    这类席位上，「需要 96 道」与「需要 10 道」在数据里**无法区分** ——")
        print("    §18.10 那张表的点估计不该被当成结论用。")
    if crossing:
        print(f"  · {'、'.join(crossing)}：相当比例的重采样里 Δ 跨过 0，n 直接无上界。")
        print("    Δ 本身符号都未定，用它当分母再平方，等于把未知放大成一个具体数字。")
    print("  · 结论层面必须退一步：**「四席够不着」没有被建立**，")
    print("    它是一个基于 5–6 道题的点估计，且与另一条算法差 7–60 倍。")
    print("    真正站得住的说法只有：当前 5–6 道 holdout **判不出任何东西**，")
    print("    所以加题一定有用；至于加到 60 道够不够，**现在还不知道**。")
    print("  · 对配法的影响：per_dim=21 仍然是个不坏的选择（更多题不会更差），")
    print("    但它的理由要从「反算出 55 道保本」降级为「现有题量确定不够，先加到额度允许的上限」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
