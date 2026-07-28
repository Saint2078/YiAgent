"""Genome bank load + G1–G5 assemble (Host + alleles → system)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SLOTS = ("G1", "G2", "G3", "G4", "G5")

DEFAULT_BANK = Path(__file__).resolve().parent / "data" / "default_bank.json"


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
    discipline: str | None = None,
) -> str:
    """Assemble contestant system: host + G1–G5 allele texts + load discipline."""
    slots = variant.get("slots") or {}
    parts = [(host or "").strip() or "你是一个有用的助手。"]
    for s in SLOTS:
        aid = slots.get(s)
        if aid:
            parts.append(allele_text(bank, aid))
    parts.append(
        discipline
        or (
            "## 装载纪律\n"
            "- 先满足边界与自检，再追求文采。\n"
            "- 输出正文本身，不要输出基因元数据。"
        )
    )
    return "\n\n".join(parts)


def assemble_from_ids(
    *,
    host: str,
    bank: dict[str, Any] | str | Path | None = None,
    variant_id: str,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Return (system, bank, variant)."""
    b = load_bank(bank)
    v = get_variant(b, variant_id)
    return assemble_system(host, b, v), b, v
