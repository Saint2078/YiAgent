"""Improve-pack: export CLI session → factory seed for neighborhood gene search."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yiagent.genome import get_variant, load_bank
from yiagent.home import ensure_home, get_home
from yiagent import sessions as sesslib

KIND = "yiagent.improve_pack"
SLOTS = ("G1", "G2", "G3", "G4", "G5")


def improve_dir(home: Path | None = None) -> Path:
    d = ensure_home(home) / "improve"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _allele_lookup(bank: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for slot, rows in (bank.get("alleles") or {}).items():
        for a in rows or []:
            if isinstance(a, dict) and a.get("id"):
                out[str(a["id"])] = {
                    "id": a["id"],
                    "label": a.get("label"),
                    "text": a.get("text"),
                    "slot": slot,
                }
    return out


def slot_texts_from_variant(bank: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    lookup = _allele_lookup(bank)
    slots = variant.get("slots") or {}
    out: dict[str, Any] = {}
    for slot in SLOTS:
        aid = slots.get(slot)
        allele = lookup.get(str(aid)) if aid else None
        out[slot] = {"allele_id": aid, "allele": allele}
    return out


def bank_from_seed(seed: dict[str, Any], *, case: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rebuild minimal allele bank from improve-pack / best_genome seed."""
    alleles: dict[str, list] = {s: [] for s in SLOTS}
    slots: dict[str, str] = {}
    slot_texts = seed.get("slot_texts") or {}
    raw_slots = seed.get("slots") or {}

    for slot in SLOTS:
        st = slot_texts.get(slot) if isinstance(slot_texts, dict) else None
        allele = None
        aid = None
        if isinstance(st, dict):
            allele = st.get("allele")
            aid = st.get("allele_id") or (allele or {}).get("id")
        if not aid:
            aid = raw_slots.get(slot)
        if isinstance(allele, dict) and allele.get("id"):
            alleles[slot].append(
                {
                    "id": str(allele["id"]),
                    "label": allele.get("label") or allele["id"],
                    "text": str(allele.get("text") or "").strip() or f"{slot} seed",
                }
            )
            aid = str(allele["id"])
        elif aid:
            alleles[slot].append(
                {
                    "id": str(aid),
                    "label": str(aid),
                    "text": f"{slot} seed allele (text missing).",
                }
            )
        else:
            aid = f"{slot.lower()}.seed"
            alleles[slot].append(
                {"id": aid, "label": f"{slot} seed", "text": f"{slot} seed placeholder."}
            )
        # ensure at least 2 alleles for normalize compatibility later
        if len(alleles[slot]) < 2:
            alleles[slot].append(
                {
                    "id": f"{slot.lower()}.seed.b",
                    "label": f"{slot} seed B",
                    "text": f"{slot} neighborhood placeholder.",
                }
            )
        slots[slot] = str(aid)

    vid = str(seed.get("variant_id") or "var.seed")
    title = str(seed.get("title") or vid)
    skills = seed.get("skills")
    variant: dict[str, Any] = {
        "id": vid,
        "hash": seed.get("hash") or f"yg-seed-{vid[-6:]}",
        "title": title,
        "slots": slots,
        "role_in_demo": "seed",
    }
    if skills:
        variant["skills"] = skills

    case = case or {}
    return {
        "meta": {
            "display_name": case.get("title") or title,
            "task": case.get("id") or "improve",
            "task_title": case.get("title") or title,
            "seed": True,
            "generated": False,
        },
        "alleles": alleles,
        "variants": [variant],
    }


def transcript_from_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        out.append({"role": role, "content": content.strip()[:8000]})
    return out


def case_from_session(
    *,
    transcript: list[dict[str, str]],
    oral: str,
    variant_title: str,
) -> dict[str, Any]:
    """Build a screening-case skeleton from chat (criteria left for judge, not genome)."""
    last_user = ""
    for m in reversed(transcript):
        if m.get("role") == "user":
            last_user = m["content"]
            break
    user_q = last_user or oral or "请根据对话中暴露的问题改进回答质量。"
    # Keep host light — genome carries identity
    host = (
        "你是已装载 G1–G5 基因组的选手。按基因行事完成用户任务；"
        "不要输出基因元数据。"
    )
    reqs = [
        "回答须满足对话语境中的用户目标",
        "不得编造未提供的事实",
        "结构清晰、可检验",
    ]
    if oral:
        reqs.insert(0, f"对齐改进意图：{oral[:200]}")
    return {
        "id": f"improve_{_stamp()[:8]}",
        "title": f"改进鉴定 · {variant_title}"[:80],
        "description": "由 CLI session 导出的再鉴定题（基因组邻域搜索）",
        "messages": [
            {"role": "system", "content": host},
            {"role": "user", "content": user_q[:6000]},
        ],
        "requirements": reqs,
        "criteria": {
            "任务完成度": {
                "weight": 40,
                "desc": "是否直接回应用户目标",
                "rubric": {
                    "90-100": "完整对齐目标且可检验",
                    "70-89": "大体完成，细节不足",
                    "60-69": "部分完成",
                    "0-59": "未完成或跑偏",
                },
            },
            "边界与诚实": {
                "weight": 30,
                "desc": "不编造、遵守角色边界",
                "rubric": {
                    "90-100": "无编造，边界清晰",
                    "70-89": "偶有含糊",
                    "60-69": "边界松",
                    "0-59": "编造或越界",
                },
            },
            "结构清晰": {
                "weight": 30,
                "desc": "表达结构与可操作性",
                "rubric": {
                    "90-100": "结构清楚可执行",
                    "70-89": "可读",
                    "60-69": "散乱",
                    "0-59": "难以理解",
                },
            },
        },
        "oral": oral,
    }


def build_improve_pack(
    session: dict[str, Any],
    *,
    bank: dict[str, Any] | None = None,
    failure_notes: str = "",
    oral: str | None = None,
) -> dict[str, Any]:
    """Build pack from persisted CLI session record."""
    bank = bank or load_bank()
    vid = str(session.get("variant_id") or "")
    try:
        variant = get_variant(bank, vid) if vid else (bank.get("variants") or [{}])[0]
    except KeyError:
        variant = (bank.get("variants") or [{}])[0]
        vid = str(variant.get("id") or "var.unknown")

    transcript = transcript_from_messages(session.get("messages") or [])
    intent = (oral or "").strip()
    if not intent:
        # first user turn as intent hint
        for m in transcript:
            if m["role"] == "user":
                intent = m["content"][:240]
                break
    if not intent:
        intent = f"改进基因组 {variant.get('title') or vid}"

    case = case_from_session(
        transcript=transcript,
        oral=intent,
        variant_title=str(variant.get("title") or vid),
    )
    seed = {
        "variant_id": vid,
        "title": variant.get("title") or vid,
        "hash": variant.get("hash"),
        "slots": dict(variant.get("slots") or {}),
        "slot_texts": slot_texts_from_variant(bank, variant),
        "skills": list(variant.get("skills") or []),
    }
    return {
        "kind": KIND,
        "version": 1,
        "saved_at": _now(),
        "session_id": session.get("id"),
        "oral": intent,
        "case": case,
        "seed": seed,
        "transcript": transcript[-40:],
        "failure_notes": (failure_notes or "").strip(),
        "model": session.get("model"),
    }


def pack_from_best_genome(best: dict[str, Any], *, failure_notes: str = "") -> dict[str, Any]:
    """Normalize factory best_genome JSON into improve-pack."""
    seed = {
        "variant_id": best.get("variant_id"),
        "title": best.get("title"),
        "hash": best.get("hash"),
        "slots": best.get("slots") or {},
        "slot_texts": best.get("slot_texts") or {},
        "skills": best.get("skills") or [],
    }
    case = best.get("case") if isinstance(best.get("case"), dict) else {}
    # ensure messages for factory
    if not case.get("messages"):
        case = case_from_session(
            transcript=[],
            oral=str(best.get("oral") or case.get("title") or "改进鉴定"),
            variant_title=str(seed.get("title") or seed.get("variant_id") or "seed"),
        )
    return {
        "kind": KIND,
        "version": 1,
        "saved_at": _now(),
        "session_id": best.get("session_id"),
        "oral": best.get("oral") or case.get("title") or "",
        "case": case,
        "seed": seed,
        "transcript": best.get("transcript") or [],
        "failure_notes": failure_notes or str((best.get("champ_summary") or {})),
        "model": best.get("model"),
        "source": "best_genome",
    }


def normalize_incoming_pack(data: dict[str, Any]) -> dict[str, Any]:
    """Accept improve_pack or best_genome-shaped JSON."""
    if not isinstance(data, dict):
        raise ValueError("pack must be an object")
    if data.get("kind") == KIND and data.get("seed"):
        return data
    if data.get("slot_texts") or (data.get("variant_id") and data.get("slots")):
        return pack_from_best_genome(data)
    if data.get("seed") and data.get("case"):
        out = dict(data)
        out["kind"] = KIND
        out["version"] = int(data.get("version") or 1)
        return out
    raise ValueError("unrecognized pack: need yiagent.improve_pack or best_genome fields")


def write_improve_pack(pack: dict[str, Any], home: Path | None = None) -> Path:
    root = improve_dir(home)
    sid = pack.get("session_id") or "session"
    path = root / f"{_stamp()}_improve_{sid}_v1.0.json"
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def apply_best_genome(best: dict[str, Any] | Path, home: Path | None = None) -> dict[str, Any]:
    """Write bank fragment + set config agent.variant / agent.bank."""
    from yiagent.config_store import load_config, save_config, set_nested

    home = home or get_home()
    if isinstance(best, Path) or (isinstance(best, str) and Path(best).is_file()):
        best = json.loads(Path(best).read_text(encoding="utf-8"))
    assert isinstance(best, dict)

    if isinstance(best.get("bank"), dict) and (
        best["bank"].get("variants") or best["bank"].get("alleles")
    ):
        bank = best["bank"]
        vid = str(
            best.get("variant_id")
            or (bank.get("variants") or [{}])[0].get("id")
            or "var.seed"
        )
        ids = {v.get("id") for v in (bank.get("variants") or []) if isinstance(v, dict)}
        if vid not in ids and bank.get("variants"):
            vid = str(bank["variants"][0].get("id"))
    else:
        if best.get("kind") == KIND:
            seed = best.get("seed") or {}
            case = best.get("case")
        else:
            seed = {
                "variant_id": best.get("variant_id"),
                "title": best.get("title"),
                "hash": best.get("hash"),
                "slots": best.get("slots") or {},
                "slot_texts": best.get("slot_texts") or {},
                "skills": best.get("skills") or [],
            }
            case = best.get("case")
        bank = bank_from_seed(seed, case=case if isinstance(case, dict) else None)
        vid = str(seed.get("variant_id") or bank["variants"][0]["id"])

    banks = ensure_home(home) / "banks"
    banks.mkdir(parents=True, exist_ok=True)
    bank_path = banks / "improved.json"
    bank_path.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")

    cfg = load_config(home)
    set_nested(cfg, "agent.variant", vid)
    set_nested(cfg, "agent.bank", str(bank_path))
    save_config(cfg, home)
    return {"variant_id": vid, "bank_path": str(bank_path), "config": str(home / "config.yaml")}


def export_from_session_id(
    session_id: str | None = None,
    *,
    failure_notes: str = "",
    oral: str | None = None,
    bank_path: str | Path | None = None,
    home: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    home = home or get_home()
    if session_id:
        rec = sesslib.resolve_session(session_id, home)
        if not rec:
            raise FileNotFoundError(f"session not found: {session_id}")
    else:
        rec = sesslib.latest_session(source="tui", home=home)
        if not rec:
            rec = sesslib.latest_session(source=None, home=home)
        if not rec:
            raise FileNotFoundError("no sessions to export")

    bank = load_bank(bank_path) if bank_path else load_bank()
    # Prefer bank path from session if present later
    pack = build_improve_pack(rec, bank=bank, failure_notes=failure_notes, oral=oral)
    path = write_improve_pack(pack, home)
    return pack, path
