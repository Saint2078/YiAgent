"""Skills = external gene cassettes (gene-bearing tool packs).

A Skill is not a sixth chromosome. It is a portable package that carries:
- allele fragments (mainly G3 / G4 / G5)
- optional tool specs the runtime may register

Variant field: ``"skills": ["skill.foo", ...]`` or bank-level defaults.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Skills may only inject into these slots (identity/persona stay core-genome).
SKILL_SLOTS = ("G3", "G4", "G5")

SKILLS_DIR = Path(__file__).resolve().parent / "data" / "skills"


def load_skill(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load one skill pack from id, path, or dict."""
    if isinstance(source, dict):
        return _normalize_skill(source)
    raw = str(source)
    path = Path(raw)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_skill(data)
    # Treat as skill id → data/skills/{id}.json
    sid = raw.removeprefix("skill.") if raw.startswith("skill.") else raw
    candidates = [
        SKILLS_DIR / f"{sid}.json",
        SKILLS_DIR / f"skill.{sid}.json",
        Path(raw),
    ]
    for c in candidates:
        if c.is_file():
            return _normalize_skill(json.loads(c.read_text(encoding="utf-8")))
    raise FileNotFoundError(f"skill not found: {source}")


def _normalize_skill(data: dict[str, Any]) -> dict[str, Any]:
    sid = str(data.get("id") or "").strip()
    if not sid:
        raise ValueError("skill missing id")
    if not sid.startswith("skill."):
        sid = f"skill.{sid}"
    genes: dict[str, list] = {}
    raw_genes = data.get("genes") or {}
    if isinstance(raw_genes, dict):
        for slot in SKILL_SLOTS:
            items = raw_genes.get(slot) or []
            if isinstance(items, list):
                genes[slot] = [a for a in items if isinstance(a, dict) and a.get("id")]
    tools = []
    for t in data.get("tools") or []:
        if isinstance(t, dict) and t.get("name"):
            tools.append(t)
    return {
        "id": sid,
        "label": data.get("label") or sid,
        "kind": data.get("kind") or "gene_cassette",
        "description": data.get("description") or "",
        "genes": genes,
        "tools": tools,
        "meta": data.get("meta") or {},
    }


def resolve_skill_ids(
    bank: dict[str, Any] | None,
    variant: dict[str, Any] | None,
    extra: list[str] | None = None,
) -> list[str]:
    ids: list[str] = []
    for src in (
        (bank or {}).get("skills"),
        (variant or {}).get("skills"),
        extra,
    ):
        if isinstance(src, list):
            for x in src:
                if x and str(x) not in ids:
                    ids.append(str(x))
    return ids


def load_skills(
    bank: dict[str, Any] | None = None,
    variant: dict[str, Any] | None = None,
    *,
    skill_ids: list[str] | None = None,
    skill_dirs: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Load skill packs referenced by bank/variant/explicit ids."""
    ids = resolve_skill_ids(bank, variant, skill_ids)
    if not ids:
        return []
    search_dirs = [SKILLS_DIR, *(skill_dirs or [])]
    out: list[dict[str, Any]] = []
    for sid in ids:
        loaded = None
        try:
            loaded = load_skill(sid)
        except FileNotFoundError:
            for d in search_dirs:
                for name in (f"{sid}.json", f"{sid.removeprefix('skill.')}.json"):
                    p = d / name
                    if p.is_file():
                        loaded = load_skill(p)
                        break
                if loaded:
                    break
        if not loaded:
            raise FileNotFoundError(f"skill not found: {sid}")
        out.append(loaded)
    return out


def skill_gene_sections(skills: list[dict[str, Any]]) -> list[str]:
    """Render skill-carried alleles as system sections."""
    parts: list[str] = []
    for sk in skills:
        label = sk.get("label") or sk.get("id")
        header = f"## Skill · {sk.get('id')} · {label}"
        body_bits = [header]
        if sk.get("description"):
            body_bits.append(str(sk["description"]).strip())
        genes = sk.get("genes") or {}
        for slot in SKILL_SLOTS:
            for a in genes.get(slot) or []:
                aid = a.get("id") or "allele"
                alabel = a.get("label") or aid
                text = (a.get("text") or "").strip()
                body_bits.append(f"### [{slot}] {aid} · {alabel}\n{text}")
        # Tools that carry a gene hint (procedure overlay for that tool)
        for t in sk.get("tools") or []:
            hint = (t.get("gene_hint") or t.get("gene") or "").strip()
            if hint:
                body_bits.append(
                    f"### [tool:{t.get('name')}] gene\n{hint}"
                )
        parts.append("\n\n".join(body_bits))
    return parts


def skill_openai_tools(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert skill tool specs → OpenAI function-calling tools list."""
    out: list[dict[str, Any]] = []
    for sk in skills:
        for t in sk.get("tools") or []:
            name = t.get("name")
            if not name:
                continue
            params = t.get("parameters") or {
                "type": "object",
                "properties": {},
            }
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": t.get("description")
                        or f"Skill tool from {sk.get('id')}",
                        "parameters": params,
                    },
                    "_skill_id": sk.get("id"),
                    "_handler": t.get("handler"),  # optional: python dotted path / builtin
                }
            )
    return out
