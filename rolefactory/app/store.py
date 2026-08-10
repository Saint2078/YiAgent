"""run 落盘：原子写 + 列表。run 目录下 state.json（快照）/ report.json / results.jsonl。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import SETTINGS


def ensure_dirs() -> None:
    SETTINGS.runs_dir.mkdir(parents=True, exist_ok=True)
    SETTINGS.cache_dir.mkdir(parents=True, exist_ok=True)


def run_dir(run_id: str) -> Path:
    d = SETTINGS.runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    ensure_dirs()
    out: list[dict[str, Any]] = []
    for d in sorted(SETTINGS.runs_dir.iterdir(), reverse=True) if SETTINGS.runs_dir.is_dir() else []:
        if not d.is_dir():
            continue
        state = read_json(d / "state.json")
        if not isinstance(state, dict):
            continue
        out.append(
            {
                "run_id": state.get("run_id"),
                "role": state.get("role"),
                "role_id": state.get("role_id"),
                "status": state.get("status"),
                "phase": state.get("phase"),
                "created_at": state.get("created_at"),
                "wall_seconds": state.get("wall_seconds"),
                "champion_score": ((state.get("champion") or {}).get("weighted")),
                "baseline_score": ((state.get("baseline") or {}).get("weighted")),
                "total_tokens": (state.get("llm") or {}).get("total_tokens"),
            }
        )
        if len(out) >= limit:
            break
    return out


def save_suite(role_id: str, cases: list[dict], blueprint: dict) -> Path:
    """题库沉淀：与已有 factory 的 case 目录格式一致（role/<role_id>/testcases.jsonl）。"""
    home = Path(os.environ.get("RF_CASE_HOME", str(SETTINGS.data_dir / "case")))
    path = home / "role" / role_id / "testcases.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for c in cases:
            row = {
                "id": c["id"],
                "level": c["level"],
                "title": c["title"],
                "description": c.get("description", ""),
                "messages": c["messages"],
                "requirements": c.get("requirements") or [],
                "criteria": c.get("criteria") or {},
                "checks": c.get("checks") or [],
                "reference_answer": c.get("reference_answer") or [],
                "tags": ["role", role_id, c["dimension_key"], c.get("scoring") or "judge"],
                "meta": {
                    "dimension": c["dimension"],
                    "dimension_key": c["dimension_key"],
                    "scoring": c.get("scoring") or "judge",
                    "trap": c.get("trap", ""),
                    "ground_truth": c.get("ground_truth") or {},
                    "verify": c.get("verify") or {},
                    "source": "rolefactory",
                },
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    write_json(path.parent / "blueprint.json", blueprint)
    return path
