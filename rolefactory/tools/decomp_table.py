#!/usr/bin/env python3
"""六席方差分解汇总：每席该加重复、该加题，还是根本判不了。

为什么要按席位分开看：`PERF.md` §10.1 曾用项目经理一席得出「只能加题、别加重复」
并把它当通则。六席都分解之后这条通则站不住 —— 题间差异占比从 **0% 到 88%**，
处方完全相反。全局套用会在一半席位上把额度花在没用的那一维。

口径（reps≥2 才能拆）：
    每题分差方差  Var(d) = σ²_b + 2σ²_w / r
    区间半宽      HW(n, r) = 1.96 · √(σ²_b + 2σ²_w/r) / √n
    r→∞ 的下限    1.96 · σ_b / √n      ← 加重复再多也降不到它以下

用法：python tools/decomp_table.py [--md]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from build_devteam import TEAM  # noqa: E402
from variance_decomp import Z95, decompose, half_width, load_cells  # noqa: E402

WB = ROOT.parent / "console" / "_workbench" / "AgentTeam" / "Develop"


def seat_run(seat: str) -> str | None:
    p = WB / seat / "genome.json"
    if not p.is_file():
        return None
    return ((json.loads(p.read_text(encoding="utf-8")).get("source") or {}).get("run_id"))


def cheapest_plan(
    var_b: float, var_w: float, delta: float, min_n: int
) -> tuple[int, int, int] | None:
    """达到「半宽 < |Δ|」最省的 (评测数, reps, 题数)。题数上限设 200，超了当不可行。

    评测数相同时**取题数少的那档**。理由是评测数没算出题成本：题间差异为 0 时
    `reps=1×167题` 与 `reps=28×6题` 都是 336 次评测，但前者要先出 167 道题
    （额度 + 泄题风险 + 出不出来都不一定），后者一道新题都不用出。

    但**题数不许低于现有题数**（`min_n`）。半宽那个公式是正态近似，题数太小就失效；
    而区间本身是**对题重采样**的自助区间 —— 1 道题没有可重采样的变异，
    算出来的「106 次评测就够」是公式的产物、不是可执行的方案。
    减题还会削弱泛化宣称本身（holdout 要覆盖各维度，不只是把区间做窄）。
    """
    if not delta:
        return None
    plans = []
    for r in range(1, 61):
        need_n = max(min_n, math.ceil((Z95 / delta) ** 2 * (var_b + 2 * var_w / r)))
        if need_n > 200:
            continue
        if half_width(var_b, var_w, need_n, r) >= delta:
            continue  # 被 min_n 抬上来之后仍不达标就不算方案
        plans.append((2 * need_n * r, need_n, r))
    if not plans:
        return None
    evals, need_n, r = min(plans)
    return (evals, r, need_n)


def plan_with_existing_cases(
    var_b: float, var_w: float, delta: float, n: int, max_reps: int = 200
) -> tuple[int, int] | None:
    """只加重复、**不出新题**能不能判出来：返回 (评测数, 所需 reps)。

    这一列才是「明天能不能动手」的答案 —— 加重复只花评测额度，加题要先出题。
    题间差异撑起的下限高于 |Δ| 时无解（那种情况重复多少次都不够）。
    """
    if not delta:
        return None
    for r in range(1, max_reps + 1):
        if half_width(var_b, var_w, n, r) < delta:
            return (2 * n * r, r)
    return None


def analyse_seat(seat: str) -> dict[str, Any]:
    run_id = seat_run(seat)
    if not run_id:
        return {"seat": seat, "err": "无落盘基因组"}
    try:
        cells, champ, base, _, detail = load_cells(run_id, "medium_02")
    except SystemExit as e:
        return {"seat": seat, "run_id": run_id, "err": str(e)[:60]}
    d = decompose(cells, champ, base)
    if d.get("var_between") is None:
        return {"seat": seat, "run_id": run_id, "reps": d.get("reps"),
                "err": f"reps={d.get('reps')}，拆不开"}

    var_b, var_w, n, r = d["var_between"], d["var_within"], d["cases"], d["reps"]
    delta = abs(d["mean_delta"] or 0)
    floor = Z95 * math.sqrt(var_b) / math.sqrt(n) if var_b > 0 else 0.0
    plan = cheapest_plan(var_b, var_w, delta, n)
    return {
        "seat": seat, "run_id": run_id, "cases": n, "reps": r,
        "delta": d["mean_delta"], "sd_delta": d["sd_delta_observed"],
        "sd_within": d["sd_within"], "sd_between": d["sd_between"],
        "between_share": d.get("between_share"),
        "hw": round(half_width(var_b, var_w, n, r), 2),
        "floor": round(floor, 2),
        "plan": plan,
        "plan_existing": plan_with_existing_cases(var_b, var_w, delta, n),
        "detail": detail,
    }


def prescription(row: dict[str, Any]) -> str:
    """按 σ_b 与 σ_w 的相对大小给处方。这是本工具唯一的「结论」，其余都是量。"""
    if row.get("err"):
        return row["err"]
    share = row.get("between_share")
    if row["floor"] >= abs(row["delta"] or 0) and row["floor"] > 0:
        return f"**只能加题**（{row['cases']} 题的下限 {row['floor']} ≥ |Δ|，重复无用）"
    if share is None or share == 0:
        return "**加重复或加题等价**（题间差异≈0，两者都在 √ 下）"
    if share >= 0.6:
        return f"**优先加题**（题间差异占 {share:.0%}）"
    return f"**优先加重复**（题间差异只占 {share:.0%}）"


def main() -> int:
    ap = argparse.ArgumentParser(description="六席方差分解汇总")
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    rows = [analyse_seat(m["seat"]) for m in TEAM]
    head = ("席位", "题×重复", "Δ配对", "σ_w噪声", "σ_b题间", "题间占比",
            "半宽", "下限", "**只加重复（不出新题）**", "最省配法", "处方")
    out = []
    for r in rows:
        if r.get("err") and "cases" not in r:
            out.append((r["seat"], "—", "—", "—", "—", "—", "—", "—", "—", "—", r["err"]))
            continue
        p = r.get("plan")
        plan_s = f"reps={p[1]}×{p[2]}题（{p[0]}次）" if p else ">200 题，不可行"
        pe = r.get("plan_existing")
        pe_s = f"**reps={pe[1]}（{pe[0]}次）**" if pe else "做不到（下限高于 |Δ|）"
        share = r.get("between_share")
        out.append((
            r["seat"], f"{r['cases']}×{r['reps']}", f"{r['delta']:+}",
            str(r["sd_within"]), str(r["sd_between"]),
            f"{share:.0%}" if share is not None else "0%",
            str(r["hw"]), str(r["floor"]), pe_s, plan_s, prescription(r),
        ))

    if args.md:
        print("| " + " | ".join(head) + " |")
        print("|" + "|".join(["---"] * len(head)) + "|")
        for r in out:
            print("| " + " | ".join(r) + " |")
    else:
        w = [max(len(str(x[i])) for x in [head, *out]) for i in range(len(head))]
        for x in [head, *out]:
            print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(x)))

    ok = [r for r in rows if r.get("plan")]
    now = [r for r in rows if r.get("plan_existing")]
    print(f"\n{len(ok)}/{len(rows)} 席存在 ≤200 题的可行配法；"
          f"**{len(now)}/{len(rows)} 席不用出新题、只加重复就够**：")
    for r in sorted(now, key=lambda x: x["plan_existing"][0]):
        pe = r["plan_existing"]
        print(f"  · {r['seat']:<10} reps={pe[1]:<3} × 现有 {r['cases']} 题 = {pe[0]} 次评测")
    print(
        "\n怎么用这张表：先看「只加重复」那一列 —— 有数就是明天能动手的，"
        "\n因为加重复只花评测额度；「最省配法」里要出上百道新题的，还得先解决出题。"
        "\n注：σ 只由 5–6 题估出，自身误差不小；配法当量级参考，别当精确值。"
        "\n注：表按「实测 Δ 就是真实效应」算 —— 真实效应更小时所需题量按平方放大。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
