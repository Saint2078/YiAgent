"""Assemble contestant system from allele bank + case host."""

from __future__ import annotations

from typing import Any


def host_of(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return m.get("content") or ""
    return ""


def non_system(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("role") != "system"]


def allele_text(bank: dict, allele_id: str) -> str:
    for slot_alleles in (bank.get("alleles") or {}).values():
        for a in slot_alleles:
            if a.get("id") == allele_id:
                label = a.get("label") or allele_id
                text = (a.get("text") or "").strip()
                return f"## {allele_id} · {label}\n{text}"
    return f"## {allele_id}\n"


def assemble_system(host: str, bank: dict, variant: dict) -> str:
    slots = variant.get("slots") or {}
    parts = [host.strip()]
    for s in ["G1", "G2", "G3", "G4", "G5"]:
        aid = slots.get(s)
        if aid:
            parts.append(allele_text(bank, aid))
    parts.append(
        "## 装载纪律\n- 先满足边界与自检，再追求文采。\n- 输出正文本身，不要输出基因元数据。"
    )
    return "\n\n".join(parts)


def build_messages(case: dict, system: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}] + non_system(case.get("messages") or [])


def variant_map(bank: dict) -> dict[str, dict]:
    return {v["id"]: v for v in bank.get("variants") or []}


def judge_body(case: dict) -> dict[str, Any]:
    return {
        "requirements": case.get("requirements") or [],
        "criteria": case.get("criteria") or {},
        "reference_answer": case.get("reference_answer") or [],
    }
