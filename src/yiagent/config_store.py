"""Settings (config.yaml) + secrets (.env) — Hermes-style split."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from yiagent.home import config_path, ensure_home, env_path, get_home

# Minimal YAML without requiring PyYAML for the tiny subset we write/read.
# Prefer PyYAML if installed.

_EXAMPLE_CONFIG = """\
# YiAgent config (behavior). Secrets go in .env next to this file.
model:
  default: plan/k3
agent:
  variant: var.champion
  max_turns: 16
  enable_tools: true
display:
  interface: tui   # tui | cli
runtime:
  rules: true        # builtin platform rules (not genome)
  rules_file: true   # also load ~/.yiagent/RULES.md if present
context:
  agents_md: true    # load AGENTS.md from cwd / parents
workspace: workspace
"""

_EXAMPLE_ENV = """\
# Secrets only — never commit this file.
# Pick the provider that matches model.default in config.yaml.
MOONSHOT_API_KEY=
# KIMI_PLAN_API_KEY=
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# OPENROUTER_API_KEY=
# DEEPSEEK_API_KEY=
# DASHSCOPE_API_KEY=
# ZHIPU_API_KEY=
"""


def example_config_text() -> str:
    return _EXAMPLE_CONFIG


def example_env_text() -> str:
    return _EXAMPLE_ENV


def load_dotenv_file(path: Path, *, override: bool = False) -> None:
    """Load KEY=VALUE lines into os.environ (no python-dotenv dependency)."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if not key:
            continue
        if override or key not in os.environ or not (os.environ.get(key) or "").strip():
            os.environ[key] = val


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse a tiny indented YAML subset (maps + scalars)."""
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except ImportError:
        pass

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if ":" not in raw:
            continue
        key, _, rest = raw.lstrip(" ").partition(":")
        key = key.strip()
        val = rest.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not val:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            elif re.fullmatch(r"-?\d+", val):
                parent[key] = int(val)
                continue
            elif val.lower() in ("true", "false"):
                parent[key] = val.lower() == "true"
                continue
            parent[key] = val
    return root


def _dump_simple_yaml(data: dict[str, Any], indent: int = 0) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except ImportError:
        pass
    lines: list[str] = []
    pad = "  " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(_dump_simple_yaml(v, indent + 1).rstrip("\n"))
        elif isinstance(v, bool):
            lines.append(f"{pad}{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{pad}{k}: {v}")
    return "\n".join(lines) + "\n"


def load_config(home: Path | None = None) -> dict[str, Any]:
    path = config_path(home)
    if not path.is_file():
        return _parse_simple_yaml(_EXAMPLE_CONFIG)
    return _parse_simple_yaml(path.read_text(encoding="utf-8"))


def save_config(data: dict[str, Any], home: Path | None = None) -> Path:
    root = ensure_home(home)
    path = config_path(root)
    path.write_text(_dump_simple_yaml(data), encoding="utf-8")
    return path


def bootstrap_home(home: Path | None = None, *, force: bool = False) -> Path:
    """Seed config.yaml + .env if missing (first-boot / setup)."""
    root = ensure_home(home)
    cfg = config_path(root)
    env = env_path(root)
    if force or not cfg.is_file():
        cfg.write_text(_EXAMPLE_CONFIG, encoding="utf-8")
    if force or not env.is_file():
        env.write_text(_EXAMPLE_ENV, encoding="utf-8")
        try:
            os.chmod(env, 0o600)
        except OSError:
            pass
    return root


def apply_runtime_env(home: Path | None = None) -> Path:
    """Load .env from YIAGENT_HOME into process env; return home."""
    root = get_home() if home is None else home
    load_dotenv_file(env_path(root), override=False)
    return root


def get_nested(data: dict[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_nested(data: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value
