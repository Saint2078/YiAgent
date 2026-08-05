"""B2 导入受体：基因来源接入 + 完整性校验 + 基因 → 可运行配置。

四步流水线第 3 步「导入」的显式入口，把三类基因来源统一收口：

- 本地 bank（``~/.yiagent`` 库 JSON，含 alleles/variants）
- hof pull 落盘包（``~/.yiagent/hof/genome_{hash}.json``，``gene_hash`` + ``bank``）
- improve 导出包（``yiagent.improve_pack`` / best_genome 形态，``seed`` 重建 bank）

铁律：接入即过 :func:`yiagent.assembly.validate_genome`，
``validation.status != "ok"`` 一律 :class:`AssemblyBlocked`，禁止静默降级。

三步可审计：``load_gene_source``（基因来源）→ ``import_genome``（可运行配置包，
``markers.source`` 留来源痕）→ ``save_vector``（落盘 ``~/.yiagent/assembled/``）
→ 运行时 ``AgentSession`` 消费同一配置包。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from yiagent.assembly import (
    AssemblyBlocked,
    assemble_vector,
    hash_format_ok,
    validate_genome,
)
from yiagent.genome import get_variant
from yiagent.home import ensure_home, get_home
from yiagent.improve_pack import KIND as IMPROVE_KIND
from yiagent.improve_pack import bank_from_seed, normalize_incoming_pack

# 基因来源类别
SOURCE_BANK = "bank"
SOURCE_HOF_PACK = "hof_pack"
SOURCE_IMPROVE_PACK = "improve_pack"


@dataclass(frozen=True)
class GeneSource:
    """归一后的基因来源：bank + 选定 variant + 来源痕迹。"""

    kind: str  # SOURCE_BANK / SOURCE_HOF_PACK / SOURCE_IMPROVE_PACK
    bank: dict[str, Any]
    variant: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)


def _read_source(source: dict[str, Any] | str | Path | None) -> tuple[Any, str | None]:
    """读入来源 JSON；文件错误转成可读 AssemblyBlocked。"""
    if source is None:
        return None, None
    if isinstance(source, dict):
        return source, None
    path = Path(source)
    if not path.is_file():
        raise AssemblyBlocked([f"基因来源文件不存在: {path}"])
    try:
        return json.loads(path.read_text(encoding="utf-8")), str(path)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AssemblyBlocked([f"基因来源不是合法 JSON: {path} ({exc})"]) from exc


def _pick_variant(bank: dict[str, Any], variant_id: str | None) -> dict[str, Any]:
    variants = bank.get("variants") or []
    if variant_id:
        try:
            return get_variant(bank, variant_id)
        except KeyError as exc:
            raise AssemblyBlocked([f"variant 不存在: {variant_id}"]) from exc
    if not variants:
        raise AssemblyBlocked(["bank 无任何 variant（无基因不组装）"])
    return variants[0]


def _from_hof_pack(data: dict[str, Any], variant_id: str | None) -> tuple[dict, dict, dict]:
    """带内嵌 bank 的包（hof 落盘包 / best_genome bank 分支）：bank 优先，
    与 ``apply_best_genome`` 同一口径；自带 gene_hash 时过严格门禁并核对一致。"""
    gh = str(data.get("gene_hash") or "").strip()
    if gh and not hash_format_ok(gh):
        raise AssemblyBlocked([f"hof 包 gene_hash 格式非法: {gh!r}"])
    bank = data.get("bank")
    if not isinstance(bank, dict) or not bank.get("alleles") or not bank.get("variants"):
        raise AssemblyBlocked(["基因来源缺少完整 bank（alleles/variants），数据不完整"])
    if variant_id:
        variant = _pick_variant(bank, variant_id)
    elif gh:
        # 默认取与 gene_hash 对应的基因组；无匹配再退首个
        variant = next(
            (v for v in bank["variants"] if str(v.get("hash") or "") == gh),
            None,
        ) or _pick_variant(bank, None)
    else:
        variant = _pick_variant(bank, str(data.get("variant_id") or "") or None)
    declared = str(variant.get("hash") or "").strip()
    if gh and declared and declared != gh:
        raise AssemblyBlocked(
            [f"hof 包 gene_hash 与基因组不一致: 包 {gh} vs variant {declared}"]
        )
    kind = SOURCE_HOF_PACK if gh else SOURCE_BANK
    provenance: dict[str, Any] = {"kind": kind}
    if gh:
        provenance["gene_hash"] = gh
    return bank, variant, provenance


def _from_improve_pack(data: dict[str, Any], variant_id: str | None) -> tuple[dict, dict, dict]:
    """improve / best_genome 包：seed 重建 bank（与 --apply 同一口径）。"""
    try:
        pack = normalize_incoming_pack(data)
    except ValueError as exc:
        raise AssemblyBlocked([f"improve 包无法识别: {exc}"]) from exc
    seed = pack.get("seed") or {}
    case = pack.get("case") if isinstance(pack.get("case"), dict) else None
    bank = bank_from_seed(seed, case=case)
    variant = _pick_variant(bank, variant_id or str(seed.get("variant_id") or "") or None)
    return bank, variant, {
        "kind": SOURCE_IMPROVE_PACK,
        "gene_hash": str(seed.get("hash") or variant.get("hash") or ""),
    }


def load_gene_source(
    source: dict[str, Any] | str | Path | None = None,
    *,
    variant_id: str | None = None,
) -> GeneSource:
    """统一基因来源入口：识别来源形态 → 归一 → 过完整性校验。

    ``source=None`` 走默认打包 bank。任何形态残缺或校验不过都抛
    :class:`AssemblyBlocked`——接入层不放行坏基因。
    """
    data, origin = _read_source(source)
    if data is None:
        # 默认库即本地 bank 来源
        from yiagent.genome import load_bank

        bank = load_bank(None)
        variant = _pick_variant(bank, variant_id)
        provenance: dict[str, Any] = {"kind": SOURCE_BANK, "path": "packaged:default_bank"}
    elif not isinstance(data, dict):
        raise AssemblyBlocked(["基因来源必须是 JSON 对象"])
    elif isinstance(data.get("bank"), dict):
        bank, variant, provenance = _from_hof_pack(data, variant_id)
    elif data.get("kind") == IMPROVE_KIND or data.get("slot_texts") or (
        data.get("variant_id") and data.get("slots")
    ):
        bank, variant, provenance = _from_improve_pack(data, variant_id)
    elif "variants" in data or "alleles" in data:
        bank = data
        variant = _pick_variant(bank, variant_id)
        provenance = {"kind": SOURCE_BANK}
    else:
        raise AssemblyBlocked(
            ["无法识别的基因来源：既非 bank，也非 hof 落盘包 / improve 导出包"]
        )
    if origin:
        provenance = {**provenance, "path": origin}

    # 接入即校验：status != ok 一律 Blocked，禁止静默降级
    report = validate_genome(bank, variant)
    if report["status"] != "ok":
        raise AssemblyBlocked(report["errors"], report=report)
    return GeneSource(kind=provenance["kind"], bank=bank, variant=variant, provenance=provenance)


def capability_checks(variant: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    """B2C 挂载清单核对：装配产物的能力清单 ↔ 基因声明逐项对账。

    - 工具清单：``runtime.skill_tools`` 必须与 markers 中各 Skill 声明的工具一致
      （双向等集：声明未装、挂载未声明都算不一致——越界工具无处藏身）
    - 槽位挂载：基因声明的等位与 markers 各槽挂载状态一致（mounted / default_skip）
    - 人设落字：已挂载等位的 id 必须真实出现在 ``runtime.genome_system``
      （G1 身份 / G2 硬边界只进 markers 不进 system 文本 = 人设未挂载）
    """
    checks: list[dict[str, Any]] = []
    markers = pack.get("markers") or {}
    runtime = pack.get("runtime") or {}

    declared_tools = sorted(
        {t for s in markers.get("skills") or [] for t in s.get("tools") or []}
    )
    runtime_tools = sorted(str(t) for t in runtime.get("skill_tools") or [])
    checks.append(
        {
            "name": "capability.tools_match",
            "ok": declared_tools == runtime_tools,
            "detail": ""
            if declared_tools == runtime_tools
            else f"声明 {declared_tools} vs 运行时 {runtime_tools}",
        }
    )

    declared_slots = variant.get("slots") or {}
    slot_markers = markers.get("slots") or {}
    mismatches: list[str] = []
    for slot, entry in slot_markers.items():
        aid = str(declared_slots.get(slot) or "").strip()
        mounted = str((entry or {}).get("allele_id") or "").strip()
        state = (entry or {}).get("state")
        if aid and (mounted != aid or state != "mounted"):
            mismatches.append(f"{slot}: 声明 {aid} vs 挂载 {mounted or state}")
        if not aid and state != "default_skip":
            mismatches.append(f"{slot}: 未声明却 {state}")
    checks.append(
        {
            "name": "capability.slot_mounts",
            "ok": not mismatches,
            "detail": "; ".join(mismatches),
        }
    )

    genome_text = str(runtime.get("genome_system") or "")
    unmounted = [
        f"{slot}:{aid}"
        for slot, entry in slot_markers.items()
        if (entry or {}).get("state") == "mounted"
        and (aid := str((entry or {}).get("allele_id") or "").strip())
        and aid not in genome_text
    ]
    checks.append(
        {
            "name": "capability.genome_text",
            "ok": not unmounted,
            "detail": f"已挂载等位未进基因组文本: {'; '.join(unmounted)}" if unmounted else "",
        }
    )
    return checks


def import_genome(
    source: dict[str, Any] | str | Path | None = None,
    *,
    host: str = "",
    variant_id: str | None = None,
    skill_ids: list[str] | None = None,
    assembled_at: str | None = None,
) -> dict[str, Any]:
    """B2B 基因 → 可运行配置：来源接入 → 校验 → 装配 expression_vector 配置包。

    产物即运行时可直接消费的配置包（``runtime.genome_system`` /
    ``runtime.skill_tools``），``markers.source`` 记录来源痕迹；
    任何一步校验不过都抛 :class:`AssemblyBlocked`。
    """
    src = load_gene_source(source, variant_id=variant_id)
    pack = assemble_vector(
        host,
        bank=src.bank,
        variant=src.variant,
        skill_ids=skill_ids,
        assembled_at=assembled_at,
    )
    pack["markers"]["source"] = dict(src.provenance)

    # B2C：能力清单核对进 validation.checks，不一致同样 Blocked
    validation = pack["markers"]["validation"]
    checks = capability_checks(src.variant, pack)
    validation["checks"].extend(checks)
    bad = [c for c in checks if not c["ok"]]
    if bad:
        errors = [f"{c['name']}: {c['detail']}" for c in bad]
        validation["errors"].extend(errors)
        validation["status"] = "blocked"
        raise AssemblyBlocked(errors, report=validation)
    return pack


def _safe_name(gene_hash: str) -> str:
    """gene_hash 转文件名安全串（与 hof_pull 同一口径）。"""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", gene_hash)[:128] or "unknown"


def save_vector(
    pack: dict[str, Any],
    out_dir: str | Path | None = None,
    *,
    home: Path | None = None,
) -> Path:
    """配置包落盘：默认 ``~/.yiagent/assembled/vector_{gene_hash}.json``（幂等覆盖）。"""
    root = Path(out_dir) if out_dir else ensure_home(home or get_home()) / "assembled"
    root.mkdir(parents=True, exist_ok=True)
    gh = str((pack.get("markers") or {}).get("gene_hash") or "unknown")
    path = root / f"vector_{_safe_name(gh)}.json"
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


__all__ = [
    "SOURCE_BANK",
    "SOURCE_HOF_PACK",
    "SOURCE_IMPROVE_PACK",
    "GeneSource",
    "capability_checks",
    "import_genome",
    "load_gene_source",
    "save_vector",
]
