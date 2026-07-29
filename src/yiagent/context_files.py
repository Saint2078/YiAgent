"""Project context files — AGENTS.md (Hermes-compatible); not part of genome."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MAX_AGENTS_CHARS = 20_000


def find_agents_md(cwd: str | Path | None) -> Path | None:
    """Find AGENTS.md in cwd, then walk parents (stop at filesystem root)."""
    if cwd is None:
        return None
    cur = Path(cwd).resolve()
    for _ in range(24):
        candidate = cur / "AGENTS.md"
        if candidate.is_file():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def load_agents_md(
    cwd: str | Path | None,
    *,
    cfg: dict[str, Any] | None = None,
) -> str:
    """Load AGENTS.md as context section, or empty string.

    Config (under ``context``):
      agents_md: true|false  — default true
    """
    ctx = (cfg or {}).get("context") if isinstance((cfg or {}).get("context"), dict) else {}
    ctx = ctx or {}
    if not bool(ctx.get("agents_md", True)):
        return ""
    path = find_agents_md(cwd)
    if not path:
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ""
    if len(text) > MAX_AGENTS_CHARS:
        head = int(MAX_AGENTS_CHARS * 0.7)
        tail = MAX_AGENTS_CHARS - head
        text = text[:head] + "\n\n…(AGENTS.md truncated)…\n\n" + text[-tail:]
    return f"## AGENTS.md（项目上下文 · {path}）\n{text}"
