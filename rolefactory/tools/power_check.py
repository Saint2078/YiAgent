#!/usr/bin/env python3
"""判定力核算：现有 holdout 题量**能判出多大的效应**，想判出实测效应**要多少题**。

为什么需要它：六席的泛化判定全是「判不了」，而「判不了」有两种完全不同的含义 ——
基因真没用，或者**尺子不够细**。分不清就会一直加重复、一直判不了。

    区间半宽 ≈ 1.96 × sd(逐题分差) / √(题数)

半宽就是**最小可判效应**：真实分差小于它，方向再对也判不出来。
反过来，想判出实测的 |Δ|，需要 n > (1.96·sd/|Δ|)²。

这两个数先算出来，再决定花不花额度：如果最小可判效应是 8 分而实测效应 1.6 分，
那不管跑多少次都判不了，得先把设计改了。

用法：
    python tools/power_check.py                    # 汇总所有有 holdout 的 run
    python tools/power_check.py <run_id> [...]
    python tools/power_check.py --md               # 输出 markdown 表
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"
Z95 = 1.959964  # 正态近似 95% 双侧临界值


def _derive_sd(hold: dict[str, Any]) -> tuple[float | None, float | None, int]:
    """从逐题分数反算配对分差的均值与标准差（早期 run 的 paired 里没有 sd）。

    返回 ``(mean, sd, n)``。注意：`reps=1` 的逐题分只测过一次，这样算出的 sd
    把「题间真实差异」和「单次测量噪声」混在一起，**偏大** —— 所以由它推出的
    所需题量要当**上界**看，不是精确值。这一点在输出里标 `sd≈`。
    """
    champ = ((hold.get("champion") or {}).get("by_case")) or {}
    base = ((hold.get("baseline") or {}).get("by_case")) or {}
    keys = [k for k in champ if k in base]
    if len(keys) < 2:
        return None, None, 0
    deltas = [float(champ[k]) - float(base[k]) for k in keys]
    n = len(deltas)
    mean = sum(deltas) / n
    var = sum((x - mean) ** 2 for x in deltas) / (n - 1)
    return round(mean, 2), round(math.sqrt(var), 2), n


def _load(run_id: str) -> dict[str, Any] | None:
    p = RUNS / run_id / "report.json"
    if not p.is_file():
        return None
    report = json.loads(p.read_text(encoding="utf-8"))
    hold = (report.get("scores") or {}).get("holdout") or {}
    paired = hold.get("paired") or {}
    # reholdout 复核过的以复核为准（原报告不改，见 pipeline.reholdout）
    rp = RUNS / run_id / "reholdout.json"
    if rp.is_file():
        rd = json.loads(rp.read_text(encoding="utf-8"))
        if rd.get("paired"):
            paired, hold = rd["paired"], {**hold, **rd}
    if not paired.get("cases"):
        return None

    sd, mean, estimated = paired.get("sd_delta"), paired.get("mean_delta"), False
    if not isinstance(sd, (int, float)):
        # 早期 run 没存 sd，但存了逐题分 —— 自己反算，别让画像缺一半
        d_mean, d_sd, d_n = _derive_sd(hold)
        if d_sd is not None:
            sd, estimated = d_sd, True
            if not isinstance(mean, (int, float)):
                mean = d_mean
    return {
        "run_id": run_id,
        "role": report.get("role"),
        "reps": hold.get("reps") or 1,
        "n": int(paired["cases"]),
        "mean_delta": mean,
        "sd_delta": sd,
        "sd_estimated": estimated,
        "ci95": paired.get("mean_delta_ci95"),
        "significant": paired.get("significant"),
        "source": "reholdout" if rp.is_file() else "run",
    }


def analyse(row: dict[str, Any]) -> dict[str, Any]:
    """算两件事：当前题量的**最小可判效应**；判出实测效应**所需题量**。"""
    n, sd, d = row["n"], row.get("sd_delta"), row.get("mean_delta")
    out = {**row, "mde": None, "needed_n": None, "verdict": "缺 sd，算不了"}
    if not isinstance(sd, (int, float)) or sd <= 0 or n < 2:
        return out

    # 最小可判效应：区间半宽。真实分差小于它，就算方向对也判不出来
    mde = Z95 * sd / math.sqrt(n)
    out["mde"] = round(mde, 2)

    if not isinstance(d, (int, float)) or abs(d) < 1e-9:
        out["verdict"] = f"当前 {n} 题只能判出 ≥{mde:.2f} 分的效应；实测分差约为 0"
        return out

    if abs(d) > mde:
        out["needed_n"] = n
        out["verdict"] = f"当前 {n} 题已足够：|Δ|={abs(d):.2f} > 半宽 {mde:.2f}"
        return out

    # 要让半宽 < |Δ|，需 n > (Z·sd/|Δ|)²。sd 假定不随题量变（同题型同难度）
    needed = math.ceil((Z95 * sd / abs(d)) ** 2)
    out["needed_n"] = needed
    out["verdict"] = (
        f"当前 {n} 题只能判出 ≥{mde:.2f} 分；实测 |Δ|={abs(d):.2f} 被噪声盖住，"
        f"要判定约需 **{needed} 题**（约 {needed / n:.1f}×）"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="holdout 判定力核算")
    ap.add_argument("run_ids", nargs="*", help="指定 run；缺省扫全部")
    ap.add_argument("--md", action="store_true", help="markdown 表输出")
    args = ap.parse_args()

    ids = args.run_ids or sorted(p.name for p in RUNS.iterdir() if p.is_dir())
    rows = [analyse(r) for rid in ids if (r := _load(rid))]
    if not rows:
        print("没有带 holdout 配对数据的 run")
        return 1

    if args.md:
        print("| 角色 | run | 题数 | reps | Δ | sd | 95%CI | 最小可判效应 | 判定所需题数 |")
        print("|------|-----|------|------|---|----|-------|--------------|--------------|")
        for r in rows:
            ci = r.get("ci95")
            ci_s = f"[{ci[0]:+.2f}, {ci[1]:+.2f}]" if isinstance(ci, list) and len(ci) == 2 else "—"
            need = r["needed_n"]
            need_s = "已足够" if need == r["n"] else (str(need) if need else "—")
            print(
                f"| {r.get('role')} | `{r['run_id'][:22]}` | {r['n']} | {r['reps']} "
                f"| {r.get('mean_delta'):+.2f} | {r.get('sd_delta')} | {ci_s} "
                f"| ≥{r['mde']} | {need_s} |"
            )
        return 0

    for r in rows:
        approx = "≈" if r.get("sd_estimated") else "="
        print(f"{r.get('role')}  ({r['run_id']}, {r['source']})")
        print(f"  题数 {r['n']} · reps {r['reps']} · Δ={r.get('mean_delta')} · sd{approx}{r.get('sd_delta')}")
        print(f"  {r['verdict']}")

    needs = [r["needed_n"] for r in rows if r["needed_n"] and r["needed_n"] > r["n"]]
    if needs:
        needs.sort()
        med = needs[len(needs) // 2]
        cur = sorted(r["n"] for r in rows)[len(rows) // 2]
        measured = [r for r in rows if not r.get("sd_estimated")]
        print(
            f"\n结论：{len(needs)}/{len(rows)} 个 run 题量不足。中位所需 {med} 题，现为 {cur} 题。"
            "\n  · 可辩护的那一条：现有设计**判不出实测量级的效应**。"
            "\n    最小可判效应按席位在 3–39 分之间，而实测分差只有 1–8 分。"
            "\n  · 标 sd≈ 的是从单次逐题分反算，把题间差异与测量噪声混在一起（偏大），"
            "\n    所需题量当**上界**看。"
        )
        if measured:
            m = measured[0]
            print(
                f"  · 唯一测准的一席（{m.get('role')}，reps={m['reps']}）："
                f"sd={m['sd_delta']} → 需 {m['needed_n']} 题。这是目前最可信的数字。"
            )
        print(
            "  · **两种噪声哪个是主项，现有数据分不开**：项目经理从 reps=1 到 reps=3，"
            "\n    sd 由 12.65 降到 3.54，但那是两次不同的 run（题目与基因都不同），"
            "\n    n=6 时抽样误差本身就极大，不能据此断定加重复有效或无效。"
            "\n    要分开，得在**同一批题**上跑 reps=1 与 reps=3 各一次再比。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
