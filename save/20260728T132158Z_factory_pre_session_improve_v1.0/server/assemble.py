"""Factory assemble — re-export from yiagent.genome."""

from __future__ import annotations

import json
from typing import Any

from yiagent.genome import allele_text, assemble_system, variant_map


def host_of(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return m.get("content") or ""
    return ""


def non_system(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("role") != "system"]


def build_messages(case: dict, system: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}] + non_system(case.get("messages") or [])


def criteria_dump_text(criteria: dict) -> str:
    return json.dumps(criteria or {}, ensure_ascii=False, indent=2)


def build_baseline_messages(case: dict, arm: str) -> list[dict[str, str]]:
    host = host_of(case.get("messages") or [])
    arm_u = (arm or "A").upper()
    if arm_u == "B":
        dump = criteria_dump_text(case.get("criteria") or {})
        system = (
            f"{host or ''}\n\n"
            "---\n"
            "【本场完整评分标准 · 基线 B 组】\n"
            "以下为裁判实际使用的完整评分标准原文（对照上界 / 灌标准基线）。\n\n"
            f"{dump}"
        ).strip()
    else:
        system = host or "(empty host)"
    return build_messages(case, system)


def judge_body(case: dict) -> dict[str, Any]:
    return {
        "requirements": case.get("requirements") or [],
        "criteria": case.get("criteria") or {},
        "reference_answer": case.get("reference_answer") or [],
    }


__all__ = [
    "allele_text",
    "assemble_system",
    "build_baseline_messages",
    "build_messages",
    "criteria_dump_text",
    "host_of",
    "judge_body",
    "non_system",
    "variant_map",
]
