"""benchmark 锚点检索：从策展索引里挑与角色相关的条目，作为出题的题型/口径参考。

benchmark 在这里是**锚点**，不是实跑对象：原题实跑（DABstep / DABench 等）需要数据文件与
代码执行沙箱，本服务只做文本裁判，因此只注入题型、评分口径与来源引用。
"""

from __future__ import annotations

import json
import re
from typing import Any

from .config import SETTINGS

_CJK = re.compile(r"[\u4e00-\u9fff]")


def load_index() -> dict[str, Any]:
    p = SETTINGS.bench_index
    if not p.is_file():
        return {"benchmarks": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"benchmarks": []}


def expand_terms(queries: list[str], *, limit: int = 48) -> list[str]:
    """中文无分词：按 2/3 字滑窗切片，保证「数据分析专家」能命中「数据分析」。"""
    terms: list[str] = []
    for q in queries:
        for tok in re.split(r"[\s,，、/|·()（）]+", str(q or "").lower()):
            tok = tok.strip()
            if len(tok) < 2:
                continue
            terms.append(tok)
            if _CJK.search(tok) and len(tok) > 2:
                for n in (2, 3):
                    for i in range(len(tok) - n + 1):
                        terms.append(tok[i : i + n])
    return list(dict.fromkeys(terms))[:limit]


def _score(entry: dict, terms: list[str]) -> int:
    blob = " ".join(
        [
            str(entry.get("id") or ""),
            str(entry.get("title") or ""),
            str(entry.get("about") or ""),
            " ".join(entry.get("capabilities") or []),
            " ".join(entry.get("keywords") or []),
        ]
    ).lower()
    return sum(1 for t in terms if t and t in blob)


def retrieve(role: str, queries: list[str] | None = None, *, limit: int = 5) -> list[dict[str, Any]]:
    terms = expand_terms([role, *(queries or [])])
    scored: list[tuple[int, dict]] = []
    for entry in load_index().get("benchmarks") or []:
        s = _score(entry, terms)
        if s > 0:
            scored.append((s, entry))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("id"))))
    return [
        {
            "id": e.get("id"),
            "title": e.get("title"),
            "about": e.get("about"),
            "task_shape": e.get("task_shape"),
            "scoring": e.get("scoring"),
            "path": e.get("path"),
            "pulled": bool(e.get("pulled")),
            "runnable_here": bool(e.get("runnable_here")),
            "blocked_by": e.get("blocked_by"),
            "match": s,
        }
        for s, e in scored[:limit]
    ]


def anchor_brief(anchors: list[dict[str, Any]]) -> str:
    if not anchors:
        return "（无匹配锚点，按角色常识出题）"
    lines = []
    for a in anchors:
        lines.append(
            f"- {a.get('id')} / {a.get('title')}：题型={a.get('task_shape')}；评分口径={a.get('scoring')}"
        )
    return "\n".join(lines)
