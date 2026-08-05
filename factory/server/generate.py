"""LLM generation of screening case + G1–G5 allele bank / variants."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from judge import parse_json
from llm_client import chat_completions, extract_content

SLOTS = ["G1", "G2", "G3", "G4", "G5"]


def _chat_json(api_key: str, model: str, system: str, user: str, *, max_tokens: int = 4000) -> dict:
    raw = extract_content(
        chat_completions(
            api_key,
            model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            reasoning_effort="low",
            purpose="generate",
        )
    )
    if not raw:
        raise ValueError("模型返回空内容")
    try:
        return parse_json(raw)
    except Exception as first:  # noqa: BLE001
        # one repair pass
        fix_raw = extract_content(
            chat_completions(
                api_key,
                model,
                [
                    {
                        "role": "system",
                        "content": "只输出合法 JSON 对象，不要 markdown，不要解释。",
                    },
                    {
                        "role": "user",
                        "content": f"把下面内容修复为合法 JSON 对象：\n\n{raw[:12000]}",
                    },
                ],
                max_tokens=max_tokens,
                reasoning_effort="low",
                purpose="generate",
            )
        )
        try:
            return parse_json(fix_raw)
        except Exception as second:  # noqa: BLE001
            raise ValueError(f"JSON 解析失败: {first}; repair: {second}; preview={raw[:400]}") from second


def generate_case(api_key: str, model: str, oral: str) -> dict[str, Any]:
    system = (
        "你是筛选题与评分标准设计师。只输出合法 JSON，不要 markdown。\n"
        "根据用户口述意图，设计一道可测的开放题 + 多维评分标准。\n"
        "硬性：criteria 各维 weight 之和应为 100；rubric 用 90-100/70-89/60-69/0-59 四档文字；"
        "不要把答案直接写进 system/user 题干。"
    )
    user = f"""口述意图：
{oral.strip()}

输出 schema：
{{
  "id": "task_xxx",
  "title": "短标题",
  "description": "一句话说明测什么",
  "messages": [
    {{"role":"system","content":"选手 system 角色设定（非评分标准）"}},
    {{"role":"user","content":"原题用户提问"}}
  ],
  "requirements": ["可检验要求1","要求2","要求3"],
  "criteria": {{
    "维度名": {{
      "weight": 40,
      "desc": "考察什么",
      "rubric": {{
        "90-100": "...",
        "70-89": "...",
        "60-69": "...",
        "0-59": "..."
      }}
    }}
  }},
  "reference_answer": ["参考要点或范文摘要"]
}}
要求：至少 2 个评分维度；messages 必须含 system 与 user。"""
    data = _chat_json(api_key, model, system, user, max_tokens=3500)
    return normalize_case(data, oral)


def normalize_case(data: dict, oral: str = "") -> dict[str, Any]:
    title = str(data.get("title") or "未命名筛选题").strip()
    cid = str(data.get("id") or f"task_{uuid.uuid4().hex[:8]}").strip()
    messages = data.get("messages") or []
    if not isinstance(messages, list):
        messages = []
    sys_c = ""
    user_c = ""
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("role") == "system" and not sys_c:
            sys_c = str(m.get("content") or "")
        if m.get("role") == "user" and not user_c:
            user_c = str(m.get("content") or "")
    if not user_c:
        user_c = oral.strip() or "请根据任务要求作答。"
    if not sys_c:
        sys_c = "你是专业助手，请认真完成用户给出的任务。"
    requirements = data.get("requirements") or []
    if not isinstance(requirements, list):
        requirements = [str(requirements)]
    requirements = [str(r) for r in requirements if str(r).strip()]
    criteria = data.get("criteria") or {}
    if not isinstance(criteria, dict) or not criteria:
        criteria = {
            "任务完成度": {
                "weight": 60,
                "desc": "是否满足核心要求",
                "rubric": {
                    "90-100": "充分满足",
                    "70-89": "基本满足",
                    "60-69": "部分满足",
                    "0-59": "明显不足",
                },
            },
            "论证清晰度": {
                "weight": 40,
                "desc": "结构与理由是否清楚",
                "rubric": {
                    "90-100": "清晰有力",
                    "70-89": "大体清楚",
                    "60-69": "含糊",
                    "0-59": "混乱",
                },
            },
        }
    clean_crit: dict[str, Any] = {}
    for name, meta in criteria.items():
        if not isinstance(meta, dict):
            continue
        rub = meta.get("rubric") or {}
        if isinstance(rub, list):
            rub = {str(i): str(x) for i, x in enumerate(rub)}
        elif not isinstance(rub, dict):
            rub = {"90-100": str(rub)}
        clean_crit[str(name)] = {
            "weight": float(meta.get("weight") or 0) or 10,
            "desc": str(meta.get("desc") or ""),
            "rubric": {str(k): str(v) for k, v in rub.items()},
        }
    ref = data.get("reference_answer") or []
    if isinstance(ref, str):
        ref = [ref]
    elif not isinstance(ref, list):
        ref = [str(ref)]
    return {
        "id": cid,
        "title": title,
        "description": str(data.get("description") or ""),
        "messages": [
            {"role": "system", "content": sys_c},
            {"role": "user", "content": user_c},
        ],
        "requirements": requirements,
        "criteria": clean_crit,
        "reference_answer": [str(x) for x in ref],
        "oral": oral.strip(),
    }


def bank_from_improve_seed(seed: dict, case: dict | None = None) -> dict[str, Any]:
    """Rebuild a minimal allele bank from improve-pack / best_genome seed."""
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
    variant: dict[str, Any] = {
        "id": vid,
        "hash": seed.get("hash") or f"yg-seed-{vid[-6:]}",
        "title": title,
        "slots": slots,
        "role_in_demo": "seed",
    }
    skills = seed.get("skills")
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


def refine_genomes(
    api_key: str,
    model: str,
    case: dict,
    seed: dict,
    *,
    transcript: list | None = None,
    failure_notes: str = "",
    mode: str = "local",
) -> dict[str, Any]:
    """Neighborhood search: pin G1, mutate G2/G4/G5 (+ light G3), keep seed variant.

    mode="local"（默认）：邻域精炼，固定 G1；mode="wide"：停滞期大开角重写，
    放开 G1 并鼓励与种子差异较大的策略方向。
    """
    wide = mode == "wide"
    seed_bank = bank_from_improve_seed(seed, case)
    seed_var = (seed_bank.get("variants") or [{}])[0]
    seed_slots = dict(seed_var.get("slots") or {})
    seed_alleles = seed_bank.get("alleles") or {}

    slim_case = {
        "title": case.get("title"),
        "description": case.get("description"),
        "requirements": case.get("requirements"),
        "user": next(
            (m.get("content") for m in (case.get("messages") or []) if m.get("role") == "user"),
            "",
        ),
    }
    seed_texts = {}
    for slot in SLOTS:
        aid = seed_slots.get(slot)
        text = ""
        for a in seed_alleles.get(slot) or []:
            if a.get("id") == aid:
                text = a.get("text") or ""
                break
        seed_texts[slot] = {"allele_id": aid, "text": text[:1200]}

    tx = []
    for m in (transcript or [])[-12:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            tx.append({"role": m["role"], "content": str(m.get("content") or "")[:600]})

    if wide:
        system = (
            "你是基因级 Agent 基因组重写设计师。只输出合法 JSON。\n"
            "进化已停滞，执行大开角重写：放开全部槽位（含 G1 身份），鼓励与种子差异"
            "较大的策略方向，不要只做措辞微调。\n"
            "禁止把评分标准 criteria / rubric 原文塞进任何等位基因文本。\n"
            "必须保留种子 variant（id 可用 var.seed 或原 id），并另产 5～9 个重写 variants。\n"
            "新等位 id 勿与种子 id 冲突；variants.slots 必须引用输出 alleles 中已有 id。"
        )
    else:
        system = (
            "你是基因级 Agent 基因组邻域设计师。只输出合法 JSON。\n"
            "在给定种子基因组邻域内搜索：固定 G1（只复制种子，不改写）；主变异 G2/G4/G5；"
            "G3 可轻改或不改。\n"
            "禁止把评分标准 criteria / rubric 原文塞进任何等位基因文本。\n"
            "必须保留种子 variant（id 可用 var.seed 或原 id），并另产 5～9 个邻域 variants。\n"
            "新等位 id 勿与种子 id 冲突；variants.slots 必须引用输出 alleles 中已有 id。"
        )
    user = f"""筛选题摘要：
{json.dumps(slim_case, ensure_ascii=False)}

种子基因组（母本）：
{json.dumps({"variant_id": seed_var.get("id"), "title": seed_var.get("title"), "slots": seed_texts}, ensure_ascii=False)}

对话摘要（差表现信号）：
{json.dumps(tx, ensure_ascii=False)}

失败备注：
{(failure_notes or "").strip() or "(无)"}

输出 schema：
{{
  "alleles": {{
    "G1": [{{"id":"…","label":"…","text":"…"}}],
    "G2": [{{"id":"…","label":"…","text":"…"}}],
    "G3": [{{"id":"…","label":"…","text":"…"}}],
    "G4": [{{"id":"…","label":"…","text":"…"}}],
    "G5": [{{"id":"…","label":"…","text":"…"}}]
  }},
  "variants": [
    {{"id":"var.seed","title":"种子对照","slots":{{"G1":"…","G2":"…","G3":"…","G4":"…","G5":"…"}}}}
  ]
}}"""
    data = _chat_json(api_key, model, system, user, max_tokens=4500)
    bank = normalize_bank(data, case)

    # Merge seed alleles (prefer seed texts / ids), then pin G1 on all variants.
    merged_alleles: dict[str, list] = {}
    for slot in SLOTS:
        by_id: dict[str, dict] = {}
        for a in seed_alleles.get(slot) or []:
            if isinstance(a, dict) and a.get("id"):
                by_id[str(a["id"])] = dict(a)
        for a in (bank.get("alleles") or {}).get(slot) or []:
            if isinstance(a, dict) and a.get("id"):
                aid = str(a["id"])
                if aid not in by_id:
                    by_id[aid] = dict(a)
        rows = list(by_id.values())
        if len(rows) < 2:
            rows.append(
                {
                    "id": f"{slot.lower()}.nb.fallback",
                    "label": f"{slot} nb",
                    "text": f"{slot} neighborhood fallback.",
                }
            )
        merged_alleles[slot] = rows

    g1_id = seed_slots.get("G1") or merged_alleles["G1"][0]["id"]
    # Ensure seed G1 allele exists
    if g1_id not in {a["id"] for a in merged_alleles["G1"]}:
        for a in seed_alleles.get("G1") or []:
            if a.get("id") == g1_id:
                merged_alleles["G1"].insert(0, dict(a))
                break

    valid = {s: {a["id"] for a in merged_alleles[s]} for s in SLOTS}
    variants: list[dict] = []
    seen_ids: set[str] = set()

    def _push(v: dict) -> None:
        if not isinstance(v, dict):
            return
        slots = dict(v.get("slots") or {})
        fixed = {}
        for s in SLOTS:
            aid = str(slots.get(s) or "")
            if s == "G1" and not wide:
                aid = str(g1_id)
            if aid not in valid[s]:
                aid = next(iter(valid[s]))
            fixed[s] = aid
        vid = str(v.get("id") or f"var.nb_{len(variants)}").strip()
        vid = re.sub(r"[^a-zA-Z0-9._-]", "_", vid)
        if vid in seen_ids:
            vid = f"{vid}_{len(variants)}"
        seen_ids.add(vid)
        row = {
            "id": vid,
            "hash": v.get("hash") or f"yg-{uuid.uuid4().hex[:8]}",
            "title": str(v.get("title") or vid),
            "slots": fixed,
        }
        if v.get("skills"):
            row["skills"] = v["skills"]
        variants.append(row)

    # Seed first
    seed_copy = dict(seed_var)
    seed_copy["id"] = str(seed_var.get("id") or "var.seed")
    seed_copy["title"] = str(seed_var.get("title") or "种子对照")
    _push(seed_copy)
    for v in bank.get("variants") or []:
        if str(v.get("id")) == seed_copy["id"]:
            continue
        _push(v)

    if len(variants) < 4:
        g3 = seed_slots.get("G3") or merged_alleles["G3"][0]["id"]
        for i, g2 in enumerate(merged_alleles["G2"][:3]):
            for j, g4 in enumerate(merged_alleles["G4"][:2]):
                for k, g5 in enumerate(merged_alleles["G5"][:2]):
                    _push(
                        {
                            "id": f"var.nb_{i}{j}{k}",
                            "title": f"邻域 {g2.get('label')}×{g4.get('label')}×{g5.get('label')}",
                            "slots": {
                                "G1": g1_id,
                                "G2": g2["id"],
                                "G3": g3,
                                "G4": g4["id"],
                                "G5": g5["id"],
                            },
                        }
                    )
                    if len(variants) >= 8:
                        break
                if len(variants) >= 8:
                    break
            if len(variants) >= 8:
                break

    title = (case or {}).get("title") or seed_var.get("title") or "improve"
    return {
        "meta": {
            "display_name": title,
            "task": (case or {}).get("id") or "improve",
            "task_title": title,
            "seed": True,
            "refined": True,
            "generated": True,
        },
        "alleles": merged_alleles,
        "variants": variants[:12],
    }


def generate_genomes(api_key: str, model: str, case: dict) -> dict[str, Any]:
    system = (
        "你是基因级 Agent 基因组设计师。只输出合法 JSON。\n"
        "为给定筛选题设计 G1–G5 等位基因库与 6～10 个候选基因组 variants。\n"
        "槽含义：G1 身份、G2 边界/语气、G3 知识挂载、G4 能力规划、G5 经验层。\n"
        "禁止把评分标准 criteria / rubric 原文塞进任何等位基因文本。\n"
        "每个槽至少 2 个等位；variants.slots 必须引用已存在的等位 id。"
    )
    slim = {
        "title": case.get("title"),
        "description": case.get("description"),
        "requirements": case.get("requirements"),
        "user": next(
            (m.get("content") for m in (case.get("messages") or []) if m.get("role") == "user"),
            "",
        ),
        "system_host": next(
            (m.get("content") for m in (case.get("messages") or []) if m.get("role") == "system"),
            "",
        ),
    }
    user = f"""筛选题摘要：
{json.dumps(slim, ensure_ascii=False)}

输出 schema：
{{
  "alleles": {{
    "G1": [{{"id":"g1.xxx","label":"短标签","text":"指令正文"}}],
    "G2": [{{"id":"g2.xxx","label":"...","text":"..."}}],
    "G3": [{{"id":"g3.xxx","label":"...","text":"..."}}],
    "G4": [{{"id":"g4.xxx","label":"...","text":"..."}}],
    "G5": [{{"id":"g5.xxx","label":"...","text":"..."}}]
  }},
  "variants": [
    {{
      "id":"var.xxx",
      "title":"基因组显示名",
      "slots":{{"G1":"g1.xxx","G2":"g2.xxx","G3":"g3.xxx","G4":"g4.xxx","G5":"g5.xxx"}}
    }}
  ]
}}"""
    data = _chat_json(api_key, model, system, user, max_tokens=4500)
    return normalize_bank(data, case)


def normalize_bank(data: dict, case: dict | None = None) -> dict[str, Any]:
    alleles_in = data.get("alleles") or {}
    alleles: dict[str, list] = {}
    id_set: set[str] = set()
    for slot in SLOTS:
        rows = alleles_in.get(slot) if isinstance(alleles_in, dict) else None
        if not isinstance(rows, list) or not rows:
            rows = [
                {
                    "id": f"{slot.lower()}.default.a",
                    "label": f"{slot} 默认 A",
                    "text": f"{slot} 基础指令：按任务要求稳健作答。",
                },
                {
                    "id": f"{slot.lower()}.default.b",
                    "label": f"{slot} 默认 B",
                    "text": f"{slot} 备选指令：更简洁直接地完成任务。",
                },
            ]
        cleaned = []
        for i, a in enumerate(rows):
            if not isinstance(a, dict):
                continue
            aid = str(a.get("id") or f"{slot.lower()}.a{i}").strip()
            aid = re.sub(r"[^a-zA-Z0-9._-]", "_", aid)
            if aid in id_set:
                aid = f"{aid}_{i}"
            id_set.add(aid)
            cleaned.append(
                {
                    "id": aid,
                    "label": str(a.get("label") or aid),
                    "text": str(a.get("text") or "").strip() or f"{slot} 指令",
                }
            )
        if len(cleaned) < 2:
            cleaned.append(
                {
                    "id": f"{slot.lower()}.fallback",
                    "label": f"{slot} 后备",
                    "text": f"{slot} 后备指令。",
                }
            )
            id_set.add(cleaned[-1]["id"])
        alleles[slot] = cleaned

    by_slot = {s: {a["id"] for a in alleles[s]} for s in SLOTS}
    variants_in = data.get("variants") or []
    variants: list[dict] = []
    if not isinstance(variants_in, list):
        variants_in = []
    for i, v in enumerate(variants_in):
        if not isinstance(v, dict):
            continue
        slots = v.get("slots") or {}
        if not isinstance(slots, dict):
            continue
        fixed = {}
        ok = True
        for s in SLOTS:
            aid = str(slots.get(s) or "")
            if aid not in by_slot[s]:
                # pick first allele of slot
                aid = alleles[s][0]["id"]
                ok = False
            fixed[s] = aid
        vid = str(v.get("id") or f"var.auto_{i}").strip()
        vid = re.sub(r"[^a-zA-Z0-9._-]", "_", vid)
        variants.append(
            {
                "id": vid,
                "hash": f"yg-{uuid.uuid4().hex[:8]}",
                "title": str(v.get("title") or vid),
                "slots": fixed,
                "fixed_slots": not ok,
            }
        )

    if len(variants) < 4:
        # cartesian-ish fill from first two alleles per variable slots
        g1 = alleles["G1"][0]["id"]
        g3 = alleles["G3"][0]["id"]
        for i, g2 in enumerate(alleles["G2"][:2]):
            for j, g4 in enumerate(alleles["G4"][:2]):
                for k, g5 in enumerate(alleles["G5"][:2]):
                    variants.append(
                        {
                            "id": f"var.combo_{i}{j}{k}",
                            "hash": f"yg-{uuid.uuid4().hex[:8]}",
                            "title": f"组合 {g2['label']}×{g4['label']}×{g5['label']}",
                            "slots": {
                                "G1": g1,
                                "G2": g2["id"],
                                "G3": g3,
                                "G4": g4["id"],
                                "G5": g5["id"],
                            },
                        }
                    )
                    if len(variants) >= 8:
                        break
                if len(variants) >= 8:
                    break
            if len(variants) >= 8:
                break

    # dedupe variant ids
    seen = set()
    uniq = []
    for v in variants:
        vid = v["id"]
        if vid in seen:
            vid = f"{vid}_{len(uniq)}"
            v = {**v, "id": vid}
        seen.add(vid)
        uniq.append(v)

    title = (case or {}).get("title") or "session"
    return {
        "meta": {
            "display_name": title,
            "task": (case or {}).get("id") or "session",
            "task_title": title,
            "generated": True,
        },
        "alleles": alleles,
        "variants": uniq[:12],
    }


def format_target_text(case: dict) -> str:
    sys = next((m.get("content") for m in (case.get("messages") or []) if m.get("role") == "system"), "")
    user = next((m.get("content") for m in (case.get("messages") or []) if m.get("role") == "user"), "")
    reqs = "\n".join(f"{i+1}. {r}" for i, r in enumerate(case.get("requirements") or []))
    return (
        f"标题：{case.get('title') or ''}\n"
        f"题号：{case.get('id') or ''}\n\n"
        f"system：\n{sys}\n\n"
        f"user（原题）：\n{user}\n\n"
        f"要求：\n{reqs}\n"
    )


def format_criteria_text(case: dict) -> str:
    lines = [
        f"标题：{case.get('title') or '评分标准'}",
        "说明：裁判标准不进选手基因组",
        "",
    ]
    for name, meta in (case.get("criteria") or {}).items():
        if not isinstance(meta, dict):
            continue
        lines.append(f"维度：{name}")
        lines.append(f"权重：{meta.get('weight', '')}")
        lines.append(f"说明：{meta.get('desc') or ''}")
        rub = meta.get("rubric") or {}
        if isinstance(rub, dict):
            lines.append("档位：")
            for band, text in rub.items():
                lines.append(f"  {band}：{text}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_target_text(text: str, base: dict | None = None) -> dict:
    """Best-effort parse edited target textarea back into case fields."""
    case = dict(base or {})
    messages = list(case.get("messages") or [])
    sys_c = next((m.get("content") for m in messages if m.get("role") == "system"), "")
    user_c = next((m.get("content") for m in messages if m.get("role") == "user"), "")
    title = case.get("title") or ""
    cid = case.get("id") or ""
    requirements = list(case.get("requirements") or [])

    m_title = re.search(r"标题：\s*(.+)", text)
    if m_title:
        title = m_title.group(1).strip()
    m_id = re.search(r"题号：\s*(\S+)", text)
    if m_id:
        cid = m_id.group(1).strip()
    m_sys = re.search(r"system：\s*\n([\s\S]*?)(?=\nuser|$)", text)
    if m_sys:
        sys_c = m_sys.group(1).strip()
    m_user = re.search(r"user（原题）：\s*\n([\s\S]*?)(?=\n要求：|$)", text)
    if m_user:
        user_c = m_user.group(1).strip()
    m_req = re.search(r"要求：\s*\n([\s\S]*)$", text)
    if m_req:
        req_block = m_req.group(1).strip()
        parsed = []
        for line in req_block.splitlines():
            line = re.sub(r"^\d+\.\s*", "", line.strip())
            if line:
                parsed.append(line)
        if parsed:
            requirements = parsed

    return {
        **case,
        "id": cid or case.get("id") or f"task_{uuid.uuid4().hex[:8]}",
        "title": title or case.get("title") or "未命名",
        "messages": [
            {"role": "system", "content": sys_c},
            {"role": "user", "content": user_c},
        ],
        "requirements": requirements,
    }


def parse_criteria_text(text: str, base: dict | None = None) -> dict:
    case = dict(base or {})
    criteria: dict[str, Any] = {}
    blocks = re.split(r"\n(?=维度：)", text.strip())
    for block in blocks:
        m_name = re.search(r"维度：\s*(.+)", block)
        if not m_name:
            continue
        name = m_name.group(1).strip()
        m_w = re.search(r"权重：\s*([\d.]+)", block)
        m_d = re.search(r"说明：\s*(.+)", block)
        rub = {}
        for band, body in re.findall(r"^\s{2}([^：\n]+)：\s*(.+)$", block, flags=re.M):
            rub[band.strip()] = body.strip()
        criteria[name] = {
            "weight": float(m_w.group(1)) if m_w else 10,
            "desc": m_d.group(1).strip() if m_d else "",
            "rubric": rub
            or {
                "90-100": "优",
                "70-89": "良",
                "60-69": "中",
                "0-59": "差",
            },
        }
    if criteria:
        case["criteria"] = criteria
    return case
