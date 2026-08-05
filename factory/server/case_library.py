"""Load XSCT / other suites from YiAgent/case/{source}/{suite}/."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

ROOT_FACTORY = Path(__file__).resolve().parents[1]
ROOT_YIAGENT = ROOT_FACTORY.parent


def resolve_case_roots() -> list[Path]:
    """返回可扫描的 case 来源根：每个根下是 suite 子目录（含 testcases.jsonl）。

    布局：``case/{source}/{suite}/testcases.jsonl``  
    兼容：``YIAGENT_CASE_ROOT`` 指向某一 source（如 …/case/xsct）时只扫该 source；
    若指向总 ``case/`` 目录则展开其下全部 source。
    """
    env = (os.environ.get("YIAGENT_CASE_ROOT") or "").strip()
    if env:
        p = Path(env)
        if not p.is_dir():
            return []
        # 已是 source（子目录带 jsonl）
        if any((c / "testcases.jsonl").is_file() for c in p.iterdir() if c.is_dir()):
            return [p]
        # 总 case/ 目录
        sources = [
            c
            for c in sorted(p.iterdir())
            if c.is_dir()
            and any((g / "testcases.jsonl").is_file() for g in c.iterdir() if g.is_dir())
        ]
        return sources or [p]

    case_home_candidates = [
        ROOT_YIAGENT / "case",
        Path("/app/case"),
        ROOT_FACTORY / "case",
    ]
    for home in case_home_candidates:
        if not home.is_dir():
            continue
        sources = [
            c
            for c in sorted(home.iterdir())
            if c.is_dir()
            and any((g / "testcases.jsonl").is_file() for g in c.iterdir() if g.is_dir())
        ]
        if sources:
            return sources
        # 旧式：home 直接是 suite 容器（如仅挂载了 xsct）
        if any((c / "testcases.jsonl").is_file() for c in home.iterdir() if c.is_dir()):
            return [home]
    return []


def resolve_case_root() -> Path | None:
    """兼容旧 API：返回第一个来源根（多为 xsct）。"""
    roots = resolve_case_roots()
    return roots[0] if roots else None


class CaseLibrary:
    """Indexed case catalog from jsonl suites under case/{source}/…。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._roots: list[Path] = []
        self._root: Path | None = None  # 兼容 meta().root
        self._items: list[dict[str, Any]] = []
        self._by_key: dict[tuple[str, str], dict[str, Any]] = {}
        self._loaded = False

    def _ingest_suite_dir(self, suite_dir: Path, source: str) -> None:
        jsonl = suite_dir / "testcases.jsonl"
        if not jsonl.is_file():
            return
        suite = suite_dir.name
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cid = str(raw.get("id") or "").strip()
                if not cid:
                    continue
                levels = raw.get("levels") or {}
                level_names = [
                    lv
                    for lv in ("basic", "medium", "hard")
                    if isinstance(levels.get(lv), dict)
                ]
                item = {
                    "id": cid,
                    "suite": suite,
                    "source": source,
                    "title": str(raw.get("title") or cid),
                    "description": str(raw.get("description") or ""),
                    "dimension": str(raw.get("dimension") or ""),
                    "test_type": str(raw.get("test_type") or suite),
                    "levels": level_names,
                    "_raw": raw,
                }
                self._items.append(item)
                self._by_key[(suite, cid)] = item

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._roots = resolve_case_roots()
            self._root = self._roots[0] if self._roots else None
            self._items = []
            self._by_key = {}
            for root in self._roots:
                # root 是 source（其下为 suite）或旧式直接 suite 容器
                children = [c for c in sorted(root.iterdir()) if c.is_dir()]
                if not children:
                    continue
                # 若子目录带 jsonl → root 为 suite 容器（source 名 = root.name）
                if any((c / "testcases.jsonl").is_file() for c in children):
                    source = root.name
                    for suite_dir in children:
                        self._ingest_suite_dir(suite_dir, source)
                else:
                    # root 是 case/ 总目录：再下钻一级 source
                    for source_dir in children:
                        source = source_dir.name
                        for suite_dir in sorted(source_dir.iterdir()):
                            if suite_dir.is_dir():
                                self._ingest_suite_dir(suite_dir, source)
            self._loaded = True

    def reload(self) -> None:
        with self._lock:
            self._loaded = False
        self.ensure_loaded()

    def meta(self) -> dict[str, Any]:
        self.ensure_loaded()
        suites: dict[str, int] = {}
        dims: set[str] = set()
        sources: dict[str, int] = {}
        for it in self._items:
            suites[it["suite"]] = suites.get(it["suite"], 0) + 1
            sources[it.get("source") or ""] = sources.get(it.get("source") or "", 0) + 1
            if it["dimension"]:
                dims.add(it["dimension"])
        return {
            "ok": bool(self._roots),
            "root": str(self._root) if self._root else None,
            "roots": [str(r) for r in self._roots],
            "count": len(self._items),
            "suites": suites,
            "sources": sources,
            "dimensions": sorted(dims),
            "levels": ["basic", "medium", "hard"],
        }

    def list_cases(
        self,
        *,
        suite: str | None = None,
        dimension: str | None = None,
        q: str | None = None,
        limit: int = 80,
        offset: int = 0,
    ) -> dict[str, Any]:
        self.ensure_loaded()
        qn = (q or "").strip().lower()
        suite_n = (suite or "").strip()
        dim_n = (dimension or "").strip()
        out: list[dict[str, Any]] = []
        for it in self._items:
            if suite_n and it["suite"] != suite_n:
                continue
            if dim_n and it["dimension"] != dim_n:
                continue
            if qn:
                blob = f"{it['id']} {it['title']} {it['description']} {it['dimension']}".lower()
                if qn not in blob:
                    continue
            out.append(
                {
                    "id": it["id"],
                    "suite": it["suite"],
                    "source": it.get("source") or "",
                    "title": it["title"],
                    "description": it["description"],
                    "dimension": it["dimension"],
                    "test_type": it["test_type"],
                    "levels": list(it["levels"]),
                }
            )
        total = len(out)
        page = out[offset : offset + max(1, min(limit, 200))]
        return {"ok": True, "total": total, "offset": offset, "limit": limit, "items": page}

    def get_raw(self, suite: str, case_id: str) -> dict[str, Any]:
        self.ensure_loaded()
        item = self._by_key.get((suite, case_id))
        if not item:
            raise KeyError(f"case not found: {suite}/{case_id}")
        return item["_raw"]

    def to_factory_case(self, suite: str, case_id: str, level: str = "basic") -> dict[str, Any]:
        raw = self.get_raw(suite, case_id)
        item = self._by_key.get((suite, case_id)) or {}
        levels = raw.get("levels") or {}
        lv = (level or "basic").strip().lower()
        body = levels.get(lv)
        if not isinstance(body, dict):
            available = [k for k in ("basic", "medium", "hard") if isinstance(levels.get(k), dict)]
            raise KeyError(f"level not found: {lv}; available={available}")
        return {
            "id": str(raw.get("id") or case_id),
            "title": str(raw.get("title") or case_id),
            "description": str(raw.get("description") or ""),
            "dimension": str(raw.get("dimension") or ""),
            "level": lv,
            "suite": suite,
            "source": item.get("source") or "case",
            "messages": body.get("messages") or [],
            "requirements": body.get("requirements") or [],
            "criteria": body.get("criteria") or {},
            "reference_answer": body.get("reference_answer") or [],
        }


LIBRARY = CaseLibrary()
