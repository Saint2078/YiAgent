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
