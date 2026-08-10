#!/usr/bin/env python3
"""把一道题的断言、两臂回答、逐条得分并排打出来。

用途是回答"这道题的巨大分差是真本事还是题有毛病"。看汇总分永远看不出来，
必须看**哪条断言没过**：基线掉在格式类断言上（min_items / lead_with）是一种事，
掉在 must_include 而那句话恰好抄自冠军基因文本，是完全另一种事 —— 后者叫题目泄答案，
和 §14 修掉的 numeric 泄题是同一类，只是泄的是措辞而不是数字。

用法：python tools/show_case.py <run_id> <case_id 子串> [--chars 700]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from app import objective  # noqa: E402


def load(run_id: str) -> tuple[dict, list[dict], str]:
    """只读**一份**明细：优先复核那份。

    两份混着读会得到「基线 4 次」这种数（1 次原始 + 3 次复核），
    正是今晚反复修的「数字不同源」，诊断工具自己不能犯。
    """
    d = ROOT / "data" / "runs" / run_id
    state = json.loads((d / "state.json").read_text(encoding="utf-8"))
    rh = ROOT / "data" / "runs" / f"{run_id}-reholdout" / "results.jsonl"
    src = rh if rh.is_file() else d / "results.jsonl"
    rows = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    return state, rows, ("复核" if src is rh else "原 run")


def main() -> int:
    ap = argparse.ArgumentParser(description="并排看一道题的断言与两臂回答")
    ap.add_argument("run_id")
    ap.add_argument("case")
    ap.add_argument("--chars", type=int, default=700)
    args = ap.parse_args()

    state, rows, src = load(args.run_id)
    case = next((c for c in state.get("cases") or [] if args.case in str(c.get("id"))), None)
    if not case:
        raise SystemExit(f"没找到含 {args.case!r} 的题")
    cid = case["id"]
    checks = objective.normalize_checks(case.get("checks") or [])

    print(f"题 {cid}")
    print(f"维度 {case.get('dimension')}｜难度 {case.get('level')}｜明细来源：{src}")
    print(f"\n题面：{str(case.get('title') or '')}")
    print(f"  {str(case.get('description') or '')[: args.chars]}")

    print(f"\n断言（{len(checks)} 条，已过 normalize_checks）：")
    for c in checks:
        extra = ""
        if c.get("type") == "numeric":
            extra = f" target={c.get('target')}{c.get('unit') or ''} tol={c.get('tolerance')}"
        if c.get("min") is not None:
            extra = f" min={c.get('min')}"
        syn = c.get("groups") or c.get("first_chars")
        print(f"  · w={float(c.get('weight') or 0):.1f} {c.get('type')}{extra}｜{c.get('desc')}")
        if syn:
            print(f"      {json.dumps(syn, ensure_ascii=False)[:260]}")

    by_arm: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("case") == cid:
            by_arm.setdefault(str(r.get("variant")), []).append(r)

    for arm in sorted(by_arm, key=lambda a: a != "baseline"):
        rs = sorted(by_arm[arm], key=lambda r: r.get("rep") or 0)
        scores = [r.get("score") for r in rs if isinstance(r.get("score"), (int, float))]
        print(f"\n=== {arm}｜{len(rs)} 次｜分数 {scores} ===")
        print(f"  回答（rep0，{rs[0].get('reply_chars')} 字，截前 {args.chars}）：")
        print(f"  {str(rs[0].get('reply') or '')[: args.chars]}")
        # 逐条得分是评测时就记下的，不重算 —— 重算会用当前尺子，和当时的分数不是一回事。
        # 每条给的是 0..1 的比例分（不是通过/不通过），拿到手的分 = weight × score。
        for item in (rs[0].get("checks") or []):
            s = float(item.get("score") or 0.0)
            w = float(item.get("weight") or 0.0)
            bar = "满分" if s >= 0.999 else ("零分" if s <= 0.001 else f"{s:.0%}")
            print(f"    {bar:>4}  得 {w * s:5.1f}/{w:4.1f}  {item.get('type'):<16}"
                  f"｜{str(item.get('note') or item.get('desc') or '')[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
