"""B1 构建表达载体：分槽装配规则 + 可观测标记与配置包格式。

四步流水线第 2 步「组装载体」的显式规则层，把散落在 load 逻辑里的
「基因组 JSON → 运行时配置」映射固化：

- ``SLOT_RULES``：每槽的来源字段 → 运行时挂载点 → 缺省/缺槽行为 → 校验规则
- ``validate_genome``：校验钩子（不抛异常，返回报告；B2A 完整性校验在此挂）
- ``assemble_vector``：装配入口，产物为配置包（运行时配置 + 可观测标记），
  校验失败抛 :class:`AssemblyBlocked`——无基因/坏基因不许硬组装
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yiagent.genome import (
    SLOTS,
    assemble_system,
    get_variant,
    load_bank,
    load_skills,
    resolve_skill_ids,
)
from yiagent.genome.skills import SKILL_SLOTS, skill_openai_tools

PACK_KIND = "yiagent.expression_vector"
PACK_VERSION = 1

# gene_hash 严格格式门禁（B2A 落地）：只接受三种形态——
# 名人堂规范 hash ``yg-xxxxxxxx``（8 位小写字母数字）、sha256 64 位小写 hex、
# 测试样例/种子白名单 ``yg-seed-*``（fixtures 与 improve 种子库的形态）。
# 其余一律判坏 hash，禁止宽松 token 蒙混进装配。
_HASH_RE = re.compile(r"^(?:[0-9a-f]{64}|yg-[0-9a-z]{8}|yg-seed-[A-Za-z0-9._-]{1,56})$")


def hash_format_ok(gene_hash: str) -> bool:
    """gene_hash 是否过严格格式门禁（B2A 来源接入也走同一判定）。"""
    return bool(_HASH_RE.match(str(gene_hash or "").strip()))


@dataclass(frozen=True)
class SlotRule:
    """单槽装配规则：来源 → 挂载点 → 缺槽行为 → 校验约束。"""

    slot: str  # 槽位号 G1–G5
    key: str  # 英文键（identity/persona/...）
    label: str  # 一句话语义
    required: bool  # 缺槽是否 Blocked
    mount: str  # 运行时挂载点
    on_missing: str  # 缺槽行为："block" | "default_skip"
    allow_skill: bool  # 是否允许 Skill 基因盒注入本槽


# G1 身份、G2 硬边界是表达载体的骨架，缺槽必须 Blocked；
# G3–G5 为可缺省叠加层，缺槽走 default_skip（跳过并在标记中留痕）。
SLOT_RULES: dict[str, SlotRule] = {
    "G1": SlotRule("G1", "identity", "我是谁、对外怎么自报", True, "system.genome#G1", "block", False),
    "G2": SlotRule("G2", "persona", "风格/职责/硬边界", True, "system.genome#G2", "block", False),
    "G3": SlotRule("G3", "knowledge", "以哪些已认证材料为据", False, "system.genome#G3", "default_skip", True),
    "G4": SlotRule("G4", "capability", "允许用什么手脚、怎么规划", False, "system.genome#G4", "default_skip", True),
    "G5": SlotRule("G5", "experience", "成败蒸馏的短控制信号", False, "system.genome#G5", "default_skip", True),
}


class AssemblyBlocked(ValueError):
    """基因组校验失败：装配被阻断，附带校验报告。"""

    def __init__(self, errors: list[str], report: dict[str, Any] | None = None) -> None:
        self.errors = list(errors)
        self.report = report or {"status": "blocked", "errors": self.errors, "checks": []}
        super().__init__("assembly blocked: " + "; ".join(self.errors))


def gene_hash_of(variant: dict[str, Any]) -> str:
    """variant 的基因哈希：自带 hash 字段优先，否则 slots 排序后的 sha256。

    与 factory/server/eval_cache.py 的约定保持一致。
    """
    h = str(variant.get("hash") or "").strip()
    if h:
        return h
    slots = variant.get("slots") or {}
    canon = json.dumps(sorted(slots.items()), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def allele_version(allele_id: str) -> str | None:
    """从等位 id 末尾取版本号（如 g1.identity.v1 → v1），无则 None。"""
    m = re.search(r"\.(v\d+)$", str(allele_id or ""))
    return m.group(1) if m else None


def _slot_allele_index(bank: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """槽位 → 等位 id → 等位条目 的索引。"""
    out: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in SLOTS}
    for slot, items in (bank.get("alleles") or {}).items():
        if slot not in out or not isinstance(items, list):
            continue
        for a in items:
            if isinstance(a, dict) and a.get("id"):
                out[slot][str(a["id"])] = a
    return out


def validate_genome(
    bank: dict[str, Any],
    variant: dict[str, Any],
    *,
    skills: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """校验钩子：按 SLOT_RULES 逐槽检查，返回报告而不抛异常。

    报告：``{"status": "ok"|"blocked", "errors": [...], "checks": [{name, ok, detail}]}``。
    B2A 完整性校验落地时在此追加 checks 即可。
    """
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> bool:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            errors.append(f"{name}: {detail}" if detail else name)
        return ok

    if not check("variant_is_dict", isinstance(variant, dict), "variant 必须是对象"):
        return {"status": "blocked", "errors": errors, "checks": checks}
    check("variant_id", bool(str(variant.get("id") or "").strip()), "variant 缺 id")

    declared = str(variant.get("hash") or "").strip()
    if declared:
        check("hash_format", bool(_HASH_RE.match(declared)), f"坏 hash: {declared!r}")

    slots = variant.get("slots")
    check("slots_is_dict", isinstance(slots, dict), "variant 缺 slots 映射")
    slots = slots if isinstance(slots, dict) else {}
    index = _slot_allele_index(bank if isinstance(bank, dict) else {})

    for slot in SLOTS:
        rule = SLOT_RULES[slot]
        aid = str(slots.get(slot) or "").strip()
        if not aid:
            if rule.required:
                check(f"{slot}.present", False, f"必需槽 {slot}({rule.key}) 缺槽")
            # 可选槽缺槽走 default_skip，不记错误
            continue
        allele = index[slot].get(aid)
        if not check(f"{slot}.allele_exists", allele is not None, f"{slot} 引用了不存在的等位: {aid}"):
            continue
        check(
            f"{slot}.allele_text",
            bool(str(allele.get("text") or "").strip()),
            f"等位 {aid} 缺 text 字段",
        )

    # Skill 基因盒只允许注入 G3–G5，禁止借 Skill 改写 G1/G2
    for sk in skills or []:
        sid = sk.get("id") or "?"
        for slot in (sk.get("genes") or {}):
            check(
                f"skill.{sid}.slot_scope",
                slot in SKILL_SLOTS and SLOT_RULES.get(slot, SLOT_RULES["G3"]).allow_skill,
                f"Skill {sid} 试图注入受限槽 {slot}",
            )

    # B2C 能力清单核对：基因（bank/variant）声明的 Skill 必须全部装载，
    # 声明了却没装上 = 能力清单与基因声明不一致，不许静默降级
    if skills is not None:
        loaded_ids = {str(s.get("id")) for s in skills if s.get("id")}
        for sid in resolve_skill_ids(bank if isinstance(bank, dict) else {}, variant):
            check(
                f"skill.{sid}.loaded",
                sid in loaded_ids,
                f"基因声明的 Skill 未装载: {sid}",
            )

    return {
        "status": "blocked" if errors else "ok",
        "errors": errors,
        "checks": checks,
    }


def _resolve_inputs(
    bank: dict[str, Any] | str | Path | None,
    variant: dict[str, Any] | None,
    variant_id: str | None,
    skills: list[dict[str, Any]] | None,
    skill_ids: list[str] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str]]:
    """归一装配输入；可预检的输入错误转成 AssemblyBlocked。"""
    load_errors: list[str] = []
    b = load_bank(bank)
    v = variant
    if v is None:
        if variant_id:
            try:
                v = get_variant(b, variant_id)
            except KeyError as exc:
                raise AssemblyBlocked([f"variant 不存在: {variant_id}"]) from exc
        else:
            variants = b.get("variants") or []
            if not variants:
                raise AssemblyBlocked(["bank 无任何 variant（无基因不组装）"])
            v = variants[0]
    sk = skills
    if sk is None:
        try:
            sk = load_skills(b, v, skill_ids=skill_ids)
        except FileNotFoundError as exc:
            load_errors.append(str(exc))
            sk = []
    if load_errors:
        raise AssemblyBlocked(load_errors)
    return b, v, sk or []


def assemble_vector(
    host: str,
    bank: dict[str, Any] | str | Path | None = None,
    variant: dict[str, Any] | None = None,
    *,
    variant_id: str | None = None,
    skills: list[dict[str, Any]] | None = None,
    skill_ids: list[str] | None = None,
    assembled_at: str | None = None,
) -> dict[str, Any]:
    """装配表达载体：基因组 JSON → 配置包（runtime + markers）。

    校验失败抛 :class:`AssemblyBlocked`。``assembled_at`` 可注入固定时间戳
    以保证同一基因组装配产物可复现。
    """
    b, v, sk = _resolve_inputs(bank, variant, variant_id, skills, skill_ids)
    report = validate_genome(b, v, skills=sk)
    if report["status"] != "ok":
        raise AssemblyBlocked(report["errors"], report=report)

    slots = v.get("slots") or {}
    index = _slot_allele_index(b)
    slot_markers: dict[str, dict[str, Any]] = {}
    for slot in SLOTS:
        rule = SLOT_RULES[slot]
        aid = str(slots.get(slot) or "").strip()
        entry: dict[str, Any] = {
            "key": rule.key,
            "mount": rule.mount,
            "allele_id": aid or None,
            "state": "mounted" if aid else rule.on_missing,
        }
        if aid:
            allele = index[slot].get(aid) or {}
            entry["label"] = allele.get("label") or aid
            entry["version"] = allele_version(aid)
        slot_markers[slot] = entry

    skill_tools = skill_openai_tools(sk)
    meta = b.get("meta") or {}
    provenance = meta.get("provenance")
    pack: dict[str, Any] = {
        "kind": PACK_KIND,
        "pack_version": PACK_VERSION,
        "markers": {
            "gene_hash": gene_hash_of(v),
            "variant_id": v.get("id"),
            "variant_title": v.get("title") or "",
            "role_id": meta.get("role_id") or "",
            "assembled_at": assembled_at
            or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "slots": slot_markers,
            "skills": [
                {
                    "id": s.get("id"),
                    "label": s.get("label"),
                    "version": (s.get("meta") or {}).get("version"),
                    "tools": [t.get("name") for t in s.get("tools") or [] if t.get("name")],
                }
                for s in sk
            ],
            "validation": report,
        },
        "runtime": {
            "host": (host or "").strip(),
            "genome_system": assemble_system(host, b, v, skills=sk),
            "slot_mounts": {slot: SLOT_RULES[slot].mount for slot in SLOTS},
            "skill_tools": [t["function"]["name"] for t in skill_tools],
            "precedence": "G2 > Runtime > AGENTS.md",
        },
    }
    # 基因库自带血统（如 rolefactory 实跑导出的 bank）就随载体带走：
    # 一份 holdout「判不了」的基因，装出来的实体必须自己说得清这件事，
    # 不能跟已验证的载体长得一样。没有血统的 bank 不凭空造这个键——
    # 否则既有演示载体的字节会变，逐字节复现的测试会挂。
    if isinstance(provenance, dict) and provenance:
        pack["markers"]["provenance"] = provenance
    return pack


def generalizes(pack: dict[str, Any]) -> bool | None:
    """载体所载基因是否**已证明**优于无基因基线。

    `True` 已证明 / `False` 已证伪 / `None` 判不了或没有血统。
    注意 `None` 与 `False` 都不许对外宣称更强，别把 `None` 当成好消息。
    """
    pr = (pack.get("markers") or {}).get("provenance") or {}
    v = pr.get("verdict") or {}
    g = v.get("generalizes")
    return g if isinstance(g, bool) else None


def marker_line(pack: dict[str, Any]) -> str:
    """配置包的一行可观测标记，供运行时日志/状态直接输出。"""
    m = pack.get("markers") or {}
    slots = ",".join(
        f"{s}:{((m.get('slots') or {}).get(s) or {}).get('allele_id') or '-'}" for s in SLOTS
    )
    skills = ",".join(str(x.get("id")) for x in m.get("skills") or []) or "-"
    validation = m.get("validation") or {}
    line = (
        f"[expression-vector] gene_hash={m.get('gene_hash')} variant={m.get('variant_id')}"
        f" slots={slots} skills={skills}"
        f" status={validation.get('status')} assembled_at={m.get('assembled_at')}"
    )
    # 有血统就把泛化判定挂在同一行：运行时日志里一眼看出这份基因能不能宣称更强
    pr = m.get("provenance") or {}
    if pr:
        label = (pr.get("verdict") or {}).get("label") or "未鉴定"
        line += f" generalizes={generalizes(pack)} verdict={label}"
    return line


__all__ = [
    "PACK_KIND",
    "PACK_VERSION",
    "SLOT_RULES",
    "AssemblyBlocked",
    "SlotRule",
    "allele_version",
    "assemble_vector",
    "gene_hash_of",
    "generalizes",
    "hash_format_ok",
    "marker_line",
    "validate_genome",
]
