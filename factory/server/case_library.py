"""Load XSCT / other suites from YiAgent/case/{source}/."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

ROOT_FACTORY = Path(__file__).resolve().parents[1]


def resolve_case_root() -> Path | None:
    env = (os.environ.get("YIAGENT_CASE_ROOT") or "").strip()
    candidates = [
        Path(env) if env else None,
        ROOT_FACTORY.parent / "case" / "xsct",  # local: YiAgent/case/xsct
        Path("/app/case/xsct"),  # docker mount
        ROOT_FACTORY / "case" / "xsct",
    ]
    for p in candidates:
        if p and p.is_dir():
            return p
    return None


class CaseLibrary:
    """Indexed case catalog from jsonl suites under case/xsct/."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._root: Path | None = None
        self._items: list[dict[str, Any]] = []
        self._by_key: dict[tuple[str, str], dict[str, Any]] = {}
        self._loaded = False

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._root = resolve_case_root()
            self._items = []
            self._by_key = {}
            if self._root is None:
                self._loaded = True
                return
            for suite_dir in sorted(self._root.iterdir()):
                if not suite_dir.is_dir():
                    continue
                jsonl = suite_dir / "testcases.jsonl"
                if not jsonl.is_file():
                    continue
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
                            "title": str(raw.get("title") or cid),
                            "description": str(raw.get("description") or ""),
                            "dimension": str(raw.get("dimension") or ""),
                            "test_type": str(raw.get("test_type") or suite),
                            "levels": level_names,
                            "_raw": raw,
                        }
                        self._items.append(item)
                        self._by_key[(suite, cid)] = item
            self._loaded = True

    def reload(self) -> None:
        with self._lock:
            self._loaded = False
        self.ensure_loaded()

    def meta(self) -> dict[str, Any]:
        self.ensure_loaded()
        suites: dict[str, int] = {}
        dims: set[str] = set()
        for it in self._items:
            suites[it["suite"]] = suites.get(it["suite"], 0) + 1
            if it["dimension"]:
                dims.add(it["dimension"])
        return {
            "ok": self._root is not None,
            "root": str(self._root) if self._root else None,
            "count": len(self._items),
            "suites": suites,
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
            "source": "xsct",
            "messages": body.get("messages") or [],
            "requirements": body.get("requirements") or [],
            "criteria": body.get("criteria") or {},
            "reference_answer": body.get("reference_answer") or [],
        }


LIBRARY = CaseLibrary()
