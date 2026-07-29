"""YIAGENT_HOME — durable state dir (Hermes-style HERMES_HOME)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_HOME_NAME = ".yiagent"


def get_home() -> Path:
    """Resolve durable home: $YIAGENT_HOME or ~/.yiagent."""
    raw = (os.environ.get("YIAGENT_HOME") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / DEFAULT_HOME_NAME).resolve()


def ensure_home(home: Path | None = None) -> Path:
    """Create home layout: config, workspace, sessions, logs."""
    root = home or get_home()
    for sub in ("", "workspace", "sessions", "logs", "save"):
        (root / sub if sub else root).mkdir(parents=True, exist_ok=True)
    return root


def config_path(home: Path | None = None) -> Path:
    return (home or get_home()) / "config.yaml"


def env_path(home: Path | None = None) -> Path:
    return (home or get_home()) / ".env"


def workspace_path(home: Path | None = None, *, configured: str | None = None) -> Path:
    root = home or get_home()
    rel = (configured or "workspace").strip() or "workspace"
    p = Path(rel)
    if p.is_absolute():
        return p
    return (root / p).resolve()
