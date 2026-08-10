#!/usr/bin/env python3
"""区分力住在哪类断言里：把「冠军−基线」的分差拆到每一类 check 上（离线，0 额度）。

为什么必须问这个：`NUMERIC_SHARE_TARGET` 现在拍在 0.60，理由是「假答案在 numeric 上
拿不到分」。但那只证明 numeric **不可伪造**，没证明它**能区分真实强弱**。若真实分差
其实来自关键词类断言，抬高 numeric 占比反而会把信号压掉 —— 两件事必须分开量。

做法：拿库里存好的回答，按当前口径重打，逐条 check 记「得分率」，再按类汇总：

    贡献(类) = Σ权重 × (冠军得分率 − 基线得分率) / 总权重 × 100

各类贡献相加 = 总分差（加权口径），所以能直接读出「这 X 分里有多少是 numeric 挣的」。
同时给出各类的**假答案得分率**（堆词），用来对照「可伪造 vs 能区分」。

用法：
    python tools/check_contrib.py                 # 全部客观题 run
    python tools/check_contrib.py <run_id> ...
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "data" / "runs"

from app import objective  # noqa: E402
from app.objective import score_answer  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from gameability import fake_answers  # noqa: E402


def _checks(run_id: str) -> dict[str, list[dict[str, Any]]]:
    p = RUNS / run_id / "state.json"
    if not p.is_file():
        return {}
    state = json.loads(p.read_text(encoding="utf-8"))
    return {
        c["id"]: objective.normalize_checks([dict(x) for x in (c.get("checks") or [])])
        for c in state.get("cases") or []
    }


def analyse(run_id: str) -> dict[str, Any] | None:
    rp = RUNS / run_id / "results.jsonl"
    sp = RUNS / run_id / "state.json"
    if not (rp.is_file() and sp.is_file()):
        return None
    state = json.loads(sp.read_text(encoding="utf-8"))
    if str((state.get("params") or {}).get("scoring_mode")) != "objective":
        return None
    champ = (state.get("champion") or {})
    champ_id = str(champ.get("id") or champ.get("sig") or "")
    checks = _checks(run_id)

    # (臂, 类) → 得分率列表；(臂, 类) → 权重列表
    rate: dict[tuple[str, str], list[float]] = defaultdict(list)
    weight: dict[tuple[str, str], list[float]] = defaultdict(list)
    for line in rp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if str(r.get("mode")) != "objective":
            continue
        arm, spec = str(r.get("variant")), checks.get(str(r.get("case")))
        if arm not in ("baseline", champ_id) or not spec:
            continue
        got = score_answer(str(r.get("reply") or ""), spec)
        for row in got.get("checks") or []:
            rate[(arm, row["type"])].append(float(row["score"]))
            weight[(arm, row["type"])].append(float(row["weight"]))

    if not rate:
        return None

    # 假答案（纯堆词）逐类得分率，作为「可伪造程度」的对照
    fake_rate: dict[str, list[float]] = defaultdict(list)
    for spec in checks.values():
        if not spec:
            continue
        soup = fake_answers(spec)["soup"]
        for row in score_answer(soup, spec).get("checks") or []:
            fake_rate[row["type"]].append(float(row["score"]))

    kinds = sorted({k for _, k in rate})
    total_w = sum(statistics.fmean(weight[("baseline", k)]) for k in kinds if ("baseline", k) in weight)
    rows = []
    for k in kinds:
        b, c = rate.get(("baseline", k)), rate.get((champ_id, k))
        if not b or not c:
            continue
        w = statistics.fmean(weight[("baseline", k)])
        rows.append(
            {
                "type": k,
                "weight_share": w / total_w * 100 if total_w else None,
                "baseline_rate": statistics.fmean(b) * 100,
                "champion_rate": statistics.fmean(c) * 100,
                "contribution": (statistics.fmean(c) - statistics.fmean(b)) * w / total_w * 100
                if total_w else None,
                "fake_rate": statistics.fmean(fake_rate[k]) * 100 if fake_rate.get(k) else None,
            }
        )
    return {
        "run_id": run_id,
        "role": (state.get("blueprint") or {}).get("role") or "?",
        "champion": champ_id,
        "rows": rows,
        "delta_total": sum(r["contribution"] or 0 for r in rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="把冠军−基线的分差拆到每类 check")
    ap.add_argument("runs", nargs="*")
    args = ap.parse_args()
    ids = args.runs or sorted(d.name for d in RUNS.iterdir() if (d / "results.jsonl").is_file())
    data = [d for rid in ids if (d := analyse(rid))]
    if not data:
        print("没有可分析的客观题 run")
        return 2

    print("分差拆解（同一批回答，当前打分口径；贡献之和 = 加权总分差）\n")
    for d in data:
        print(f"## {d['run_id']}  {d['role']}   总分差 {d['delta_total']:+.2f}")
        print("| 断言类 | 权重占比 | 基线得分率 | 冠军得分率 | 贡献 | 堆词得分率 |")
        print("|---|---|---|---|---|---|")
        for r in d["rows"]:
            fake = "—" if r["fake_rate"] is None else f"{r['fake_rate']:.0f}%"
            print(
                f"| {r['type']} | {r['weight_share']:.0f}% | {r['baseline_rate']:.0f}% |"
                f" {r['champion_rate']:.0f}% | **{r['contribution']:+.2f}** | {fake} |"
            )
        print()

    # 汇总：numeric 与非 numeric 各自挣了多少分差
    agg: dict[str, list[float]] = defaultdict(list)
    fake_agg: dict[str, list[float]] = defaultdict(list)
    for d in data:
        for r in d["rows"]:
            agg[r["type"]].append(r["contribution"] or 0)
            if r["fake_rate"] is not None:
                fake_agg[r["type"]].append(r["fake_rate"])
    num = statistics.fmean(agg.get("numeric") or [0])
    rest = sum(statistics.fmean(v) for k, v in agg.items() if k != "numeric")
    print("## 汇总（各 run 平均）\n")
    print(f"- numeric 贡献 **{num:+.2f}** 分；其余各类合计 **{rest:+.2f}** 分")
    if num + rest:
        print(f"- numeric 占总分差的 **{num / (num + rest) * 100:.0f}%**")
    print("\n| 断言类 | 平均贡献 | 堆词得分率 |")
    print("|---|---|---|")
    for k in sorted(agg, key=lambda x: -statistics.fmean(agg[x])):
        f = statistics.fmean(fake_agg[k]) if fake_agg.get(k) else None
        print(f"| {k} | {statistics.fmean(agg[k]):+.2f} | {'—' if f is None else f'{f:.0f}%'} |")
    print(
        "\n怎么读：\n"
        "  · 「贡献」高 = 这类断言真的在区分强弱；「堆词得分率」高 = 它同时可被伪造。\n"
        "  · 只有**贡献高且堆词拿不到**的类才配拿大权重 —— 这是调 NUMERIC_SHARE_TARGET 的依据。\n"
        "  · 贡献接近 0 而堆词得分率接近 100 的类，本质是**送分项**：抬高它只会抬高假答案地板。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
