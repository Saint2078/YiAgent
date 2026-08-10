"""对客观评分体系做对抗审计：用构造答案打真实断言，量化「可复算」之外的效度漏洞。

四种探针：
- stuff  机械堆词：把所有 target 与 must_include 首个同义词罗列出来，零分析。高分 = 假阳性漏洞。
- hedge  对冲罗列：同时写出正确值与陷阱值。高分 = numeric 只认字符串出现、不认唯一结论。
- negate 正确答案 + 含否定的正确表述（如「不建议全量上线」）。低分 = 否定盲区造成假阴性。
- empty  格式合规但空洞：只有结论行与三条废话。高分 = 形式分给太松。

用法：python tools/audit_scoring.py [testcases.jsonl] [results.jsonl]
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import objective  # noqa: E402

SUITE = "data/case/role/role_b4893b59/testcases.jsonl"


def load_jsonl(path: str) -> list[dict]:
    return [json.loads(line) for line in io.open(path, encoding="utf-8") if line.strip()]


def fmt(target: float, unit: str) -> str:
    txt = f"{target:g}"
    return txt + (unit or "")


def probe_stuff(case: dict) -> str:
    """零分析：罗列每个 numeric 的 target（带其首个定位词）与每组 must_include 的首个同义词。"""
    lines = ["结论：按下述要点处理。", "建议如下：", ""]
    for c in case["checks"]:
        if c["type"] == "numeric":
            near = (c.get("near") or [""])[0]
            lines.append(f"- {near}：{fmt(c['target'], c.get('unit') or '')}")
        elif c["type"] == "must_include":
            for g in c.get("groups") or []:
                syn = (g.get("any") or [""])[0]
                lines.append(f"- {syn}")
    while len([x for x in lines if x.startswith("- ")]) < 3:
        lines.append("- 需要进一步确认口径？")
    return "\n".join(lines)


def probe_hedge(case: dict) -> str:
    """对冲：正确值与陷阱值一起给，不做取舍。"""
    body = [probe_stuff(case), "", "另一种口径下也可能是以下数值（不确定用哪个）："]
    trap = case.get("meta", {}).get("ground_truth", {}).get("trap", "")
    for num in re.findall(r"\d+(?:\.\d+)?%?", trap)[:4]:
        body.append(f"- 也可能是 {num}")
    return "\n".join(body)


def probe_negate(case: dict) -> str:
    """正确答案 + 用否定句表达正确立场：检验禁含词的否定盲区。"""
    gt = case.get("meta", {}).get("ground_truth", {})
    lines = ["结论：先纠正口径再决策。", "", gt.get("reasoning", ""), ""]
    for c in case["checks"]:
        if c["type"] == "numeric":
            near = (c.get("near") or [""])[0]
            lines.append(f"- {near}：{fmt(c['target'], c.get('unit') or '')}")
        elif c["type"] == "must_include":
            for g in c.get("groups") or []:
                lines.append(f"- {(g.get('any') or [''])[0]}")
    for c in case["checks"]:
        if c["type"] == "must_not_include":
            for g in c.get("groups") or []:
                for bad in (g.get("any") or [])[:2]:
                    lines.append(f"- 明确反对：不能{bad}，也不应把它当达标依据。")
    return "\n".join(lines)


def probe_empty(case: dict) -> str:
    return "结论：建议谨慎推进。\n- 需要对齐指标口径？\n- 需要复核数据质量\n- 需要评估风险"


PROBES = {"stuff": probe_stuff, "hedge": probe_hedge, "negate": probe_negate, "empty": probe_empty}


def main() -> None:
    suite = sys.argv[1] if len(sys.argv) > 1 else SUITE
    cases = load_jsonl(suite)
    out: list[str] = []
    add = out.append

    add(f"# 客观评分体系 · 对抗审计（{len(cases)} 题）")
    add("")
    add("| 题 | 维度 | 堆词 | 对冲 | 否定 | 空洞 |")
    add("|----|------|------|------|------|------|")
    totals = {k: [] for k in PROBES}
    per_check_fail: dict[str, list[str]] = {}
    for c in cases:
        row = [c["id"].split("_")[-2] + "_" + c["id"].split("_")[-1], c["meta"]["dimension"]]
        for name, fn in PROBES.items():
            res = objective.score_answer(fn(c), c["checks"])
            totals[name].append(res["total"])
            row.append(f"{res['total']:.1f}")
            if name == "negate":
                for chk in res["checks"]:
                    if chk["type"] == "must_not_include" and chk["score"] < 1:
                        per_check_fail.setdefault(c["id"], []).append(f"{chk['id']}: {chk['note']}")
        add("| " + " | ".join(row) + " |")
    add("")
    for name in PROBES:
        v = totals[name]
        add(f"- **{name}** 均分 {sum(v) / len(v):.1f}（{min(v):.1f} – {max(v):.1f}）")
    add("")
    if per_check_fail:
        add("## 否定盲区（正确立场被禁含词误伤）")
        for cid, notes in per_check_fail.items():
            add(f"- {cid}：{'；'.join(notes)}")
    else:
        add("## 否定盲区：未复现")
    add("")

    # 真实评测分布：哪些断言几乎白送
    if len(sys.argv) > 2 and Path(sys.argv[2]).is_file():
        rows = load_jsonl(sys.argv[2])
        by_type: dict[str, list[float]] = {}
        full = 0
        for r in rows:
            if r.get("score") is None:
                continue
            if r["score"] >= 99.99:
                full += 1
            for chk in r.get("checks") or []:
                by_type.setdefault(chk["type"], []).append(chk["score"])
        add(f"## 真实评测分布（{len(rows)} 条）")
        add(f"- 满分条数：{full}（{full / len(rows) * 100:.1f}%）")
        for t, v in sorted(by_type.items()):
            add(f"- {t}：平均得分率 {sum(v) / len(v):.3f}，全通率 {sum(1 for x in v if x >= 0.999) / len(v):.3f}，n={len(v)}")

    dest = Path("tools/AUDIT.md")
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"written {dest}")


if __name__ == "__main__":
    main()
