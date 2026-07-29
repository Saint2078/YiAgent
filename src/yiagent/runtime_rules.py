"""Runtime rules — platform layer; never stored in the genome bank."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from yiagent.home import get_home

# Built-in platform rules (Hermes-style task/tool guidance, YiAgent-thin).
DEFAULT_RUNTIME_RULES = """\
## Runtime rules（平台层 · 不进基因组）
- 冲突优先级：**G2 硬边界 > Runtime rules > AGENTS.md**。
- 禁止编造未读到的文件内容、未执行的命令输出、未验证的事实。
- 需要读写或执行时，优先使用提供的工具；工具失败时展示可见错误，勿装作成功。
- Skills 是外部基因盒：可带来工具与 G3/G4/G5 片段，不改写 G1/G2。
- 输出正文本身，不要输出基因元数据或槽位编号表演。
"""

MAX_RULES_CHARS = 12_000


def rules_path(home: Path | None = None) -> Path:
    return (home or get_home()) / "RULES.md"


def load_runtime_rules(
    *,
    home: Path | None = None,
    cfg: dict[str, Any] | None = None,
    builtin: str | None = None,
) -> str:
    """Compose runtime rules from builtin + optional ~/.yiagent/RULES.md.

    Config (under ``runtime``):
      rules: true|false          — inject builtin (default true)
      rules_file: true|false     — load RULES.md if present (default true)
    """
    rt = (cfg or {}).get("runtime") if isinstance((cfg or {}).get("runtime"), dict) else {}
    rt = rt or {}
    use_builtin = bool(rt.get("rules", True))
    use_file = bool(rt.get("rules_file", True))

    parts: list[str] = []
    if use_builtin:
        parts.append((builtin or DEFAULT_RUNTIME_RULES).strip())

    if use_file:
        path = rules_path(home)
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                if len(text) > MAX_RULES_CHARS:
                    text = text[:MAX_RULES_CHARS] + "\n\n…(RULES.md truncated)"
                parts.append(f"## RULES.md（{path}）\n{text}")

    return "\n\n".join(parts)
