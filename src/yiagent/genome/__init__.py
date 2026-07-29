"""Genome bank load + G1–G5 assemble + Skills (gene cassettes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .skills import (
    SKILL_SLOTS,
    load_skill,
    load_skills,
    resolve_skill_ids,
    skill_gene_sections,
    skill_openai_tools,
)

SLOTS = ("G1", "G2", "G3", "G4", "G5")

DEFAULT_BANK = Path(__file__).resolve().parent / "data" / "default_bank.json"

__all__ = [
    "DEFAULT_BANK",
    "SKILL_SLOTS",
    "SLOTS",
    "allele_text",
    "assemble_from_ids",
    "assemble_system",
    "get_variant",
    "load_bank",
    "load_skill",
    "load_skills",
    "resolve_skill_ids",
    "skill_gene_sections",
    "skill_openai_tools",
    "variant_map",
]


def load_bank(source: str | Path | dict[str, Any] | None = None) -> dict[str, Any]:
    """Load allele bank from path or dict; default packaged critical-thinker demo."""
    if source is None:
        source = DEFAULT_BANK
    if isinstance(source, dict):
        return source
    path = Path(source)
    return json.loads(path.read_text(encoding="utf-8"))


def variant_map(bank: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {v["id"]: v for v in bank.get("variants") or [] if v.get("id")}


def get_variant(bank: dict[str, Any], variant_id: str) -> dict[str, Any]:
    v = variant_map(bank).get(variant_id)
    if not v:
        known = ", ".join(variant_map(bank)) or "(empty)"
        raise KeyError(f"variant not found: {variant_id}; known: {known}")
    return v


def allele_text(bank: dict[str, Any], allele_id: str) -> str:
    for slot_alleles in (bank.get("alleles") or {}).values():
        for a in slot_alleles or []:
            if a.get("id") == allele_id:
                label = a.get("label") or allele_id
                text = (a.get("text") or "").strip()
                return f"## {allele_id} · {label}\n{text}"
    return f"## {allele_id}\n"


def assemble_system(
    host: str,
    bank: dict[str, Any],
    variant: dict[str, Any],
    *,
    skills: list[dict[str, Any]] | None = None,
    skill_ids: list[str] | None = None,
) -> str:
    """Assemble contestant genome only: host + G1–G5 + Skill cassettes.

    Platform rules and AGENTS.md are composed later via ``prompt_layers.compose_system``
    (never stored in the allele bank).
    """
    slots = variant.get("slots") or {}
    parts = [(host or "").strip() or "你是一个有用的助手。"]
    for s in SLOTS:
        aid = slots.get(s)
        if aid:
            parts.append(allele_text(bank, aid))

    loaded = skills
    if loaded is None:
        try:
            loaded = load_skills(bank, variant, skill_ids=skill_ids)
        except FileNotFoundError:
            loaded = []
    parts.extend(skill_gene_sections(loaded or []))
    return "\n\n".join(parts)


def assemble_from_ids(
    *,
    host: str,
    bank: dict[str, Any] | str | Path | None = None,
    variant_id: str,
    skill_ids: list[str] | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Return (system, bank, variant, skills)."""
    b = load_bank(bank)
    v = get_variant(b, variant_id)
    skills = load_skills(b, v, skill_ids=skill_ids)
    return assemble_system(host, b, v, skills=skills), b, v, skills
