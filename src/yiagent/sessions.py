"""Chat session persistence — Hermes-style continue/resume (JSON under YIAGENT_HOME)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yiagent.home import ensure_home, get_home


def sessions_dir(home: Path | None = None) -> Path:
    root = ensure_home(home)
    d = root / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:6]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_path(session_id: str, home: Path | None = None) -> Path:
    safe = re.sub(r"[^\w.\-]+", "_", session_id)
    return sessions_dir(home) / f"{safe}.json"


def save_session(record: dict[str, Any], home: Path | None = None) -> Path:
    record = dict(record)
    record["updated_at"] = _now_iso()
    path = session_path(str(record["id"]), home)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    # pointer for continue without workspace filter
    active = sessions_dir(home) / "active_session.json"
    active.write_text(
        json.dumps({"session_id": record["id"], "source": record.get("source")}, indent=2),
        encoding="utf-8",
    )
    return path


def load_session(session_id: str, home: Path | None = None) -> dict[str, Any] | None:
    path = session_path(session_id, home)
    if not path.is_file():
        # prefix match
        matches = list(sessions_dir(home).glob(f"{session_id}*.json"))
        matches = [p for p in matches if p.name != "active_session.json"]
        if len(matches) == 1:
            path = matches[0]
        else:
            return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("id") else None


def list_sessions(home: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sessions_dir(home).glob("*.json"):
        if p.name == "active_session.json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("id"):
            out.append(data)
    out.sort(key=lambda r: r.get("updated_at") or r.get("started_at") or "", reverse=True)
    return out


def resolve_by_title(title: str, home: Path | None = None) -> dict[str, Any] | None:
    title = title.strip()
    if not title:
        return None
    # exact title
    matches = [s for s in list_sessions(home) if (s.get("title") or "") == title]
    if matches:
        return matches[0]
    # case-insensitive
    low = title.lower()
    matches = [s for s in list_sessions(home) if (s.get("title") or "").lower() == low]
    return matches[0] if matches else None


def resolve_session(name_or_id: str, home: Path | None = None) -> dict[str, Any] | None:
    """Match exact id, id prefix, or title (Hermes --resume)."""
    raw = (name_or_id or "").strip()
    if not raw:
        return None
    hit = load_session(raw, home)
    if hit:
        return hit
    # prefix among listed
    pref = [s for s in list_sessions(home) if str(s.get("id", "")).startswith(raw)]
    if len(pref) == 1:
        return pref[0]
    return resolve_by_title(raw, home)


def latest_session(
    *,
    source: str | None = "tui",
    cwd: str | None = None,
    home: Path | None = None,
    fallback_sources: tuple[str, ...] = ("cli",),
) -> dict[str, Any] | None:
    """MRU session: prefer source+cwd, then source, then fallbacks (Hermes -c)."""
    all_s = list_sessions(home)
    if not all_s:
        return None

    def pick(src: str | None, want_cwd: bool) -> dict[str, Any] | None:
        for s in all_s:
            if src and s.get("source") != src:
                continue
            if want_cwd and cwd and (s.get("cwd") or "") != cwd:
                continue
            return s
        return None

    if source:
        if cwd:
            hit = pick(source, True)
            if hit:
                return hit
        hit = pick(source, False)
        if hit:
            return hit
    for fb in fallback_sources:
        hit = pick(fb, False)
        if hit:
            return hit
    return all_s[0]


def create_record(
    *,
    source: str,
    model: str,
    variant_id: str | None,
    cwd: str | Path,
    messages: list[dict[str, Any]],
    title: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    sid = session_id or new_session_id()
    # title from first user message if missing
    if not title:
        for m in messages:
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                title = m["content"].strip().replace("\n", " ")[:60] or None
                break
    if not title:
        title = sid
    return {
        "id": sid,
        "source": source,
        "title": title,
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
        "ended_at": None,
        "cwd": str(Path(cwd).resolve()),
        "model": model,
        "variant_id": variant_id,
        "messages": messages,
    }


def title_from_prompt(prompt: str, session_id: str) -> str:
    t = (prompt or "").strip().replace("\n", " ")[:60]
    return t or session_id
