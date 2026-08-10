#!/usr/bin/env python3
"""天花板题到底在干什么：**稀释**还是**截断**？两者的预言不同，可以直接分辨。

§18.4 我把负号归因于「截断偏负」：基线 95 分的题最多 +5、却可以 −95，上下不对称，
所以 Δ 被系统性压向负数。那条推断预言：**扔掉高基线题，Δ 应当变正**。

另一个机制预言完全不同：若天花板题两臂都是满分，它们的 Δ ≈ 0，方差也≈0。
0 对负均值来说偏**高**、对正均值来说偏**低** —— 于是这类题把 Δ 一律往 0 **稀释**，
与符号无关。它预言：扔掉之后 **|Δ| 变大**，负的更负、正的更正。

`ceiling_sweep.py` 的实测是 Dev（−0.87 → −1.60）与 Architect（−3.43 → −3.99）
扔完之后**更负** —— 与截断预言相反，与稀释预言一致。本工具直接量这两组的
Δ 均值与方差，把机制钉死。

用法：python tools/ceiling_mech.py [--ceiling 90]
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import ceiling_sweep as cs  # noqa: E402  复用取数逻辑，避免两处口径漂移


def classify(mh: float, ml: float, sh: float, sl: float) -> dict[str, str]:
    """把两组的均值/标准差判成机制标签。

    单独抽出来是有原因的：这段判读的第一版是**写死在 print 里的一句话**，
    于是在 mh=-6.27、ml=+5.21 的数据上照样印出「高基线组的 |Δ| 明显小于其余组」——
    6.27 明显大于 5.21，一句假话，而且不报错。
    抽成函数才能拿合成数据钉住它（`DilutionVsDragTests`）。
    """
    out: dict[str, str] = {}
    out["mechanism"] = "dilution" if abs(mh) < 0.25 * abs(ml) else "drag"
    out["drag_toward"] = "negative" if mh < ml else "positive"
    out["sd_effect"] = "drop_raises_sd" if sh < sl else "drop_may_lower_sd"
    out["power_claim"] = (
        "falsified" if sh < sl else "not_falsified"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="分辨天花板题是稀释还是截断")
    ap.add_argument("--ceiling", type=float, default=90.0)
    args = ap.parse_args()

    C = args.ceiling
    print(f"门槛 {C:g}：把 holdout 分成「高基线」与「其余」两组，比它们的 Δ\n")
    print("  席位            组      题数  Δ均值    Δ的sd   |Δ|  说明")
    tot_hi: list[float] = []
    tot_lo: list[float] = []
    for seat, rid in cs.SEATS:
        rows, _ = cs._load_rows(rid)
        if not rows:
            continue
        pc = cs.per_case(rows)
        hi = [v["delta"] for v in pc.values() if v["base"] > C]
        lo = [v["delta"] for v in pc.values() if v["base"] <= C]
        if not hi or not lo:
            continue
        tot_hi += hi
        tot_lo += lo
        for name, g in (("高基线", hi), ("其余", lo)):
            m = st.fmean(g)
            sd = st.stdev(g) if len(g) > 1 else 0.0
            print(f"  {seat:<14} {name:<6} {len(g):>4}  {m:>+6.2f}  {sd:>6.2f}  {abs(m):>5.2f}")
        print()

    if tot_hi and tot_lo:
        mh, ml = st.fmean(tot_hi), st.fmean(tot_lo)
        sh = st.stdev(tot_hi) if len(tot_hi) > 1 else 0.0
        sl = st.stdev(tot_lo) if len(tot_lo) > 1 else 0.0
        print("=" * 72)
        print(f"  合计  高基线 {len(tot_hi):>3} 题：Δ均值 {mh:+.2f}、sd {sh:.2f}")
        print(f"        其余   {len(tot_lo):>3} 题：Δ均值 {ml:+.2f}、sd {sl:.2f}")
        print()
        print("  判读（**由上面的数算出来的，不是预先写好的**）：")
        verdict = classify(mh, ml, sh, sl)

        # 机制一：稀释（Δ≈0）还是拖拽（Δ 系统性偏一侧）？看高基线组的 Δ 离 0 有多远
        gap = ml - mh
        if verdict["mechanism"] == "dilution":
            print(f"  · 高基线组 Δ={mh:+.2f} 接近 0（其余组 {ml:+.2f}）→ **稀释**：")
            print("    这类题几乎不产生分差，把总体 Δ 往 0 拉，与符号无关。")
        else:
            print(f"  · 高基线组 Δ={mh:+.2f}，并不接近 0；与其余组 {ml:+.2f} 差 {gap:+.2f} 分 →")
            print(f"    **拖拽**而非稀释：这类题系统性地把总体 Δ 往"
                  f"{'负' if mh < ml else '正'}的方向拉。")
            print("    这一条支持「截断偏负」（贴满分的题冠军只能往下掉），而不是「稀释到 0」。")

        # 机制二：扔掉它们会让 sd 变大还是变小？
        if verdict["sd_effect"] == "drop_raises_sd":
            print(f"  · 高基线组 sd={sh:.2f} **小于**其余组 {sl:.2f} → 它们在压低 sd。")
            print("    扔掉 → sd 变大、n 变小，半宽（≈1.96·sd/√n）**两头一起变坏**。")
            print("    故「扔了更准」被**证伪**：门槛的收益在去偏，不在提高判定力。")
        else:
            print(f"  · 高基线组 sd={sh:.2f} 不低于其余组 {sl:.2f} → 扔掉不必然抬高 sd。")

        # 机制三：逐席方向是否一致？合计的方向不能替各席作结论
        flip = []
        for seat, rid in cs.SEATS:
            rows, _ = cs._load_rows(rid)
            if not rows:
                continue
            pc = cs.per_case(rows)
            hi = [v["delta"] for v in pc.values() if v["base"] > C]
            lo = [v["delta"] for v in pc.values() if v["base"] <= C]
            if not hi or not lo:
                continue
            # 与合计方向相反 = 该席的高基线题反而是"较好"的那批
            if (st.fmean(hi) - st.fmean(lo)) * (mh - ml) < 0:
                flip.append(seat)
        if flip:
            print(f"  · **但逐席方向不一致**：{'、'.join(flip)} 的高基线题反而不是拖后腿的那批。")
            print("    合计方向由题量最大的那一席主导，**不能替各席作结论** ——")
            print("    对这些席位，扔掉天花板题会让 Δ 更负，说明那个负号不是天花板造成的。")
        print()
        print("  纪律：**不得**用 ceiling_sweep 挑一个「刚好显著」的门槛 —— 那是换了件衣服的")
        print("  事后择优（扫 9 档取最显著，等于做了 9 次比较却只报 1 次）。门槛只能按")
        print("  先验口径定（「一道题至少要有 10 分可涨空间才算能提供信息」→ 90）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
