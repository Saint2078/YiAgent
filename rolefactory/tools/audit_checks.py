#!/usr/bin/env python3
"""审计 `must_not_include`：把「引用错误说法去反驳」误判成「给出了错误说法」的比例算出来。

缺陷来自匹配方式：`_hit_must_not_include` 是纯子串匹配（`禁词 in 回答`），
命中即把这条分扣光。可是同一道题的 `must_include` 又要求答题者**显式指出陷阱**，
而指出陷阱最自然的写法就是把错误说法引出来再否掉：

    「不能仅凭 p<0.05 就说**可以上线**」   → 命中禁词「可以上线」→ 该条 0 分
    「结论：**不成立**。报表 +4pp 主要是埋点口径变更」→ 命中禁词「+4pp」→ 该条 0 分

于是两条断言互相冲突：越是把陷阱讲清楚，越容易被扣分。这不是「答题者不好」，
是**尺子本身有偏**，而且偏得不均匀（取决于答题风格），会直接变成分数噪声。

本工具只做审计（不改分、不改代码）：对每个被扣光的 `must_not_include`，
定位命中的那个词，看它前面同一句里有没有否定/反驳线索，据此把命中分成
「疑似误判」与「确实给出了错误断言」。

用法：
    python tools/audit_checks.py                    # 审计全部 run
    python tools/audit_checks.py <run_id> ...
    python tools/audit_checks.py --examples 5       # 多打几条原文
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"

# 否定/反驳线索。只用**明确**的否定词，避免把「上线前需要…」这类中性表述算成反驳。
CUES = (
    "不能",
    "不可",
    "不应",
    "不得",
    "不该",
    "不宜",
    "不足以",
    "不构成",
    "不成立",
    "不代表",
    "不等于",
    "不建议",
    "不要",
    "并非",
    "并不",
    "而非",
    "无法",
    "禁止",
    "切勿",
    "避免",
    "错误",
    "误判",
    "误读",
    "反例",
    "驳",
    "伪",
    "假设性",
    "不是",
    "非",
)
# 句子切分：只在强标点处断句。逗号不算，因为「A，不能B」正是我们要抓的结构。
SENT_SPLIT = re.compile(r"[。！？；\n]")
LOOKBACK = 60  # 同句内往前看多少字找反驳线索


def sentences(text: str) -> list[str]:
    return [s for s in SENT_SPLIT.split(text) if s.strip()]


def judge_hit(text: str, phrase: str) -> tuple[str, str]:
    """返回 (判断, 证据句)。判断 ∈ {refuted, asserted}。

    refuted = 命中词所在句里有明确否定/反驳线索 → 疑似误判
    asserted = 没有线索 → 大概率真的给出了错误断言
    """
    low, p = text.lower(), phrase.lower()
    best = ""
    for sent in sentences(text):
        if p not in sent.lower():
            continue
        idx = sent.lower().find(p)
        window = sent[max(0, idx - LOOKBACK) : idx]
        if any(c in window for c in CUES):
            return "refuted", sent.strip()
        best = best or sent.strip()
    if best:
        return "asserted", best
    # 命中词跨句（很少见）：退回整段窗口判断
    idx = low.find(p)
    window = text[max(0, idx - LOOKBACK) : idx]
    return ("refuted" if any(c in window for c in CUES) else "asserted"), text[
        max(0, idx - 80) : idx + 40
    ].strip()


def specs_of(run_id: str) -> dict[str, dict[str, Any]]:
    """题面里的 check 规格（含禁词同义词）。存在 state.json 的 cases 里。"""
    p = RUNS / run_id / "state.json"
    if not p.is_file():
        return {}
    state = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for case in state.get("cases") or []:
        for c in case.get("checks") or []:
            if str(c.get("type")) == "must_not_include":
                out[f"{case['id']}::{c.get('id')}"] = c
    return out


def phrases_of(spec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for g in spec.get("groups") or []:
        if isinstance(g, dict):
            out.extend(str(s) for s in (g.get("any") or []) if str(s).strip())
        else:
            out.append(str(g))
    return out


def audit_run(run_id: str) -> dict[str, Any]:
    rp = RUNS / run_id / "results.jsonl"
    if not rp.is_file():
        return {"run_id": run_id, "error": "缺 results.jsonl（运行时产物，未入库）"}
    specs = specs_of(run_id)
    rows = [json.loads(line) for line in rp.read_text(encoding="utf-8").splitlines() if line.strip()]

    total = zeros = refuted = 0
    weight_lost = 0.0
    weight_lost_refuted = 0.0
    examples: list[dict[str, Any]] = []

    for r in rows:
        text = str(r.get("reply") or "")
        for ck in r.get("checks") or []:
            if str(ck.get("type")) != "must_not_include":
                continue
            total += 1
            w = float(ck.get("weight") or 0)
            if float(ck.get("score") or 0) > 0:
                continue
            zeros += 1
            weight_lost += w
            spec = specs.get(f"{r.get('case')}::{ck.get('id')}") or {}
            hits = [p for p in phrases_of(spec) if p.lower() in text.lower()]
            verdicts = [judge_hit(text, p) for p in hits]
            if verdicts and all(v[0] == "refuted" for v in verdicts):
                refuted += 1
                weight_lost_refuted += w
                examples.append(
                    {
                        "case": r.get("case"),
                        "variant": r.get("variant"),
                        "check": ck.get("id"),
                        "weight": w,
                        "phrase": hits[0],
                        "sentence": verdicts[0][1][:180],
                    }
                )

    return {
        "run_id": run_id,
        "evaluations": len(rows),
        "must_not_include_checks": total,
        "zeroed": zeros,
        "suspect_misjudged": refuted,
        "weight_lost": round(weight_lost, 1),
        "weight_lost_refuted": round(weight_lost_refuted, 1),
        "examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="审计 must_not_include 的误判率")
    ap.add_argument("runs", nargs="*", help="run_id（省略则审计全部）")
    ap.add_argument("--examples", type=int, default=3, help="每个 run 打几条原文")
    args = ap.parse_args()

    run_ids = args.runs or sorted(d.name for d in RUNS.iterdir() if (d / "results.jsonl").is_file())
    if not run_ids:
        print("没有带 results.jsonl 的 run（逐条明细是运行时产物，只在跑过的机器上）")
        return 2

    agg = {"checks": 0, "zeroed": 0, "suspect": 0, "lost": 0.0, "lost_suspect": 0.0}
    for rid in run_ids:
        d = audit_run(rid)
        if d.get("error"):
            print(f"{rid}: {d['error']}")
            continue
        agg["checks"] += d["must_not_include_checks"]
        agg["zeroed"] += d["zeroed"]
        agg["suspect"] += d["suspect_misjudged"]
        agg["lost"] += d["weight_lost"]
        agg["lost_suspect"] += d["weight_lost_refuted"]
        rate = d["suspect_misjudged"] / d["zeroed"] if d["zeroed"] else 0
        print(
            f"{rid}  禁词断言 {d['must_not_include_checks']:>4} 条 ·"
            f" 被扣光 {d['zeroed']:>4} 条 · 疑似误判 {d['suspect_misjudged']:>4} 条（{rate:.0%}）"
        )
        for ex in d["examples"][: args.examples]:
            print(f"    · [{ex['variant']}] 禁词「{ex['phrase']}」权重 {ex['weight']:g}")
            print(f"      原文：{ex['sentence']}")

    if agg["zeroed"]:
        print(
            f"\n合计：{agg['zeroed']} 条被扣光，其中 **{agg['suspect']} 条疑似误判**"
            f"（{agg['suspect'] / agg['zeroed']:.0%}）。"
            f"\n被误扣的权重合计 {agg['lost_suspect']:g}（占所有扣分权重 "
            f"{agg['lost_suspect'] / agg['lost']:.0%}），换算成总分约 "
            f"{agg['lost_suspect'] / max(1, agg['checks']):.1f} 分/条评测。"
        )
        print(
            "\n判定口径：命中词所在句子里、词前 60 字内出现明确否定/反驳线索 → 记「疑似误判」。"
            "\n这是**保守**的一侧：跨句反驳（先下结论、后句才引错误说法）算不进来，真实误判可能更多。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
