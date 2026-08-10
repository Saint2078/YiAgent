"""基因库（G1-G5 等位基因）→ 变体组装 → 交叉/变异。

G1 身份定位 / G2 边界约束 / G3 知识方法 / G4 能力流程 / G5 经验风格。
每槽含一个**弱等位（对照）**，用来验证"这个槽到底有没有用"。
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

from .llm import Session

SLOTS: tuple[tuple[str, str], ...] = (
    ("G1", "身份定位"),
    ("G2", "边界约束"),
    ("G3", "知识方法"),
    ("G4", "能力流程"),
    ("G5", "经验风格"),
)

BANK_SYS = """你是「Agent DNA 设计师」。给定角色与其能力维度，为 5 个基因槽各写若干**等位基因**（allele）。

槽位定义：
- G1 身份定位：这个 Agent 是谁、为谁服务、优先级
- G2 边界约束：不做什么、信息不足时怎么办、什么必须先问
- G3 知识方法：该领域可复用的方法/框架/口径（要具体，不要"具备扎实的专业知识"）
- G4 能力流程：接到任务后的执行步骤与自检
- G5 经验风格：输出结构、语气、给结论的方式

硬要求：
1. 每槽 3 个等位：1 个 weak（刻意平庸的对照，只有一句空泛话）+ 2 个 strong（写法/侧重不同，要能被评测区分开）。
2. strong 等位是**可执行指令**，写"怎么做"，不写"很重要"。每条 60-220 字。
3. 两个 strong 等位必须走不同路线（例如 G4 一个"先对齐口径再动手"、一个"先给可用初稿再迭代"），便于评测选优。
4. 只输出 JSON，不要解释、不要代码块。

JSON 结构：
{"alleles":{"G1":[{"id":"g1_weak","label":"短标签","strength":"weak","text":"提示词片段"},
                  {"id":"g1_a","label":"...","strength":"strong","text":"...","hypothesis":"预期改善哪个维度"}],
            "G2":[...],"G3":[...],"G4":[...],"G5":[...]}}"""


async def build_bank(
    session: Session, blueprint: dict[str, Any], cases: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    dims = "\n".join(
        f"- {d['name']}（权重{d['weight']}）：{d.get('why', '')}｜易错：{'；'.join(d.get('failure_modes') or [])}"
        for d in blueprint["dimensions"]
    )
    sample = "\n".join(f"- [{c['dimension']}] {c['title']}：{c.get('description', '')}" for c in cases[:8])
    user = (
        f"角色：{blueprint['role']}（{blueprint.get('one_line', '')}）\n\n"
        f"能力维度与易错点：\n{dims}\n\n"
        f"硬边界：{'；'.join(blueprint.get('hard_constraints') or []) or '（未给）'}\n"
        f"输出习惯：{'；'.join(blueprint.get('output_habits') or []) or '（未给）'}\n\n"
        f"评测题目（了解会被怎么考）：\n{sample}\n\n请产出 5 个槽的等位基因。"
    )
    obj = await session.chat_json(
        [{"role": "system", "content": BANK_SYS}, {"role": "user", "content": user}],
        purpose="bank",
        max_tokens=16384,
        temperature=0.7,
        cache=False,  # 基因库 JSON 易截断；禁用缓存避免反复命中坏响应
    )
    return normalize_bank(obj)


def normalize_bank(obj: Any) -> dict[str, list[dict[str, Any]]]:
    raw = obj.get("alleles") if isinstance(obj, dict) else None
    if not isinstance(raw, dict):
        raise ValueError("bank 缺 alleles")
    bank: dict[str, list[dict[str, Any]]] = {}
    for slot, slot_name in SLOTS:
        items = raw.get(slot) or raw.get(slot.lower()) or []
        out: list[dict[str, Any]] = []
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            text = str(it.get("text") or "").strip()
            if not text:
                continue
            strength = str(it.get("strength") or "").strip().lower()
            if strength not in ("weak", "strong"):
                strength = "weak" if i == 0 and len(items) > 1 else "strong"
            out.append(
                {
                    "id": str(it.get("id") or f"{slot.lower()}_{i}"),
                    "slot": slot,
                    "slot_name": slot_name,
                    "label": str(it.get("label") or f"{slot_name}{i + 1}").strip(),
                    "strength": strength,
                    "text": text,
                    "hypothesis": str(it.get("hypothesis") or "").strip(),
                }
            )
        if not out:
            raise ValueError(f"bank 槽 {slot} 为空")
        bank[slot] = out
    return bank


def weak_of(bank: dict[str, list[dict]], slot: str) -> dict[str, Any]:
    for a in bank[slot]:
        if a["strength"] == "weak":
            return a
    return bank[slot][0]


def strongs_of(bank: dict[str, list[dict]], slot: str) -> list[dict[str, Any]]:
    out = [a for a in bank[slot] if a["strength"] == "strong"]
    return out or bank[slot]


def genome_text(choice: dict[str, str], bank: dict[str, list[dict]]) -> str:
    parts: list[str] = []
    for slot, slot_name in SLOTS:
        aid = choice.get(slot)
        allele = next((a for a in bank[slot] if a["id"] == aid), None)
        if allele is None:
            continue
        parts.append(f"【{slot} {slot_name}】\n{allele['text']}")
    return "\n\n".join(parts)


def sig(choice: dict[str, str]) -> str:
    blob = json.dumps({k: choice.get(k) for k, _ in SLOTS}, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def make_variant(choice: dict[str, str], bank: dict[str, list[dict]], *, gen: int, origin: str) -> dict[str, Any]:
    labels = {}
    for slot, _ in SLOTS:
        allele = next((a for a in bank[slot] if a["id"] == choice.get(slot)), None)
        labels[slot] = allele["label"] if allele else "?"
    return {
        "id": f"g{gen}_{sig(choice)}",
        "sig": sig(choice),
        "gen": gen,
        "origin": origin,
        "choice": {slot: choice.get(slot) for slot, _ in SLOTS},
        "labels": labels,
        "system": genome_text(choice, bank),
    }


BASELINE_SYSTEM = "你是一个乐于助人的助手，请认真回答用户的问题。"


def baseline_variant() -> dict[str, Any]:
    return {
        "id": "baseline",
        "sig": "baseline",
        "gen": 0,
        "origin": "baseline",
        "choice": {slot: None for slot, _ in SLOTS},
        "labels": {slot: "（无基因）" for slot, _ in SLOTS},
        "system": BASELINE_SYSTEM,
    }


def all_weak_variant(bank: dict[str, list[dict]]) -> dict[str, Any]:
    choice = {slot: weak_of(bank, slot)["id"] for slot, _ in SLOTS}
    return make_variant(choice, bank, gen=0, origin="all_weak")


def seed_population(bank: dict[str, list[dict]], n: int, rng: random.Random) -> list[dict[str, Any]]:
    """初代：全强组合 + 单槽消融（每槽退化为 weak）+ 随机组合，保证每个等位至少出现一次。"""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push(choice: dict[str, str], origin: str) -> None:
        v = make_variant(choice, bank, gen=0, origin=origin)
        if v["sig"] in seen:
            return
        seen.add(v["sig"])
        out.append(v)

    best = {slot: strongs_of(bank, slot)[0]["id"] for slot, _ in SLOTS}
    push(dict(best), "all_strong")

    for slot, _ in SLOTS:
        if len(out) >= n:
            break
        ch = dict(best)
        ch[slot] = weak_of(bank, slot)["id"]
        push(ch, f"ablate_{slot}")

    for slot, _ in SLOTS:
        for alt in strongs_of(bank, slot)[1:]:
            if len(out) >= n:
                break
            ch = dict(best)
            ch[slot] = alt["id"]
            push(ch, f"swap_{slot}")

    guard = 0
    while len(out) < n and guard < 200:
        guard += 1
        ch = {slot: rng.choice(strongs_of(bank, slot))["id"] for slot, _ in SLOTS}
        push(ch, "random")
    return out[:n]


def breed(
    elites: list[dict[str, Any]],
    bank: dict[str, list[dict]],
    n: int,
    gen: int,
    rng: random.Random,
    seen: set[str],
) -> list[dict[str, Any]]:
    """交叉：从精英按槽取样；变异：随机换 1 个槽的等位。"""
    out: list[dict[str, Any]] = []
    guard = 0
    while len(out) < n and guard < 400:
        guard += 1
        if len(elites) >= 2:
            a, b = rng.sample(elites, 2)
            choice = {
                slot: (a["choice"].get(slot) if rng.random() < 0.5 else b["choice"].get(slot))
                for slot, _ in SLOTS
            }
        else:
            choice = dict(elites[0]["choice"])
        for slot, _ in SLOTS:
            if choice.get(slot) is None:
                choice[slot] = strongs_of(bank, slot)[0]["id"]
        if rng.random() < 0.85:
            slot = rng.choice([s for s, _ in SLOTS])
            pool = [a["id"] for a in bank[slot] if a["id"] != choice.get(slot)]
            if pool:
                choice[slot] = rng.choice(pool)
        v = make_variant(choice, bank, gen=gen, origin="crossover")
        if v["sig"] in seen:
            continue
        seen.add(v["sig"])
        out.append(v)
    return out
