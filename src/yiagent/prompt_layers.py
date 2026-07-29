"""Full system prompt: Genome + Runtime + Context (precedence G2 > Runtime > AGENTS)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from yiagent.context_files import load_agents_md
from yiagent.home import get_home
from yiagent.runtime_rules import load_runtime_rules

PRECEDENCE = """\
## 装载优先级（冲突时）
1. **G2 硬边界**（基因组）
2. **Runtime rules**（平台 / RULES.md）
3. **AGENTS.md**（项目上下文）
"""


def compose_system(
    genome_system: str,
    *,
    cwd: str | Path | None = None,
    home: Path | None = None,
    cfg: dict[str, Any] | None = None,
) -> str:
    """Wrap assembled genome with runtime rules and AGENTS.md.

    Genome text must already contain host + G1–G5 + Skills.
    Rules and project context never enter the allele bank.
    """
    parts = [PRECEDENCE.strip(), (genome_system or "").strip()]
    runtime = load_runtime_rules(home=home or get_home(), cfg=cfg)
    if runtime:
        parts.append(runtime)
    agents = load_agents_md(cwd, cfg=cfg)
    if agents:
        parts.append(agents)
    return "\n\n".join(p for p in parts if p)
