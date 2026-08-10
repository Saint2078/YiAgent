#!/usr/bin/env python3
"""生成基因组工作台 v1.1：只新增 *_v1_1 pack，不覆盖原基因组。

v1.1 加厚策略（相对「每槽仅 1 个冠军等位」）：
  1) 深拷贝原 pack 全量等位基因（~50+/席）
  2) 并入该席 rolefactory report.bank 的全部等位（weak+strong）
  3) 冠军等位标记 champion=true 且 active；bank 其余 active 以便图上可见
  4) 将 blueprint 评测维写入 pack.dimensions（元数据，不另开槽位）
"""
from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONSOLE = Path(__file__).resolve().parents[2] / "console"
RUNTIME = CONSOLE / "_workbench" / "AgentTeam" / "Develop"
RUNS = Path(__file__).resolve().parents[1] / "data" / "runs"
OUT_JS = CONSOLE / "genome-packs-factory-v11.js"
OUT_JSON = CONSOLE / "_workbench" / "AgentTeam" / "genome-wb-v11-manifest.json"
DOC = Path(__file__).resolve().parents[3] / "工作台" / "AgentTeam" / "genome-wb-v11.md"

SEAT_TO_PACK = {
    "Product": "product_manager",
    "PM": "project_manager",
    "Architect": "ai_architect",
    "Dev": "develop",
    "DevOps": "devops",
}

SLOT_LABEL = {
    "G1": "身份",
    "G2": "人设边界",
    "G3": "知识",
    "G4": "落地策略",
    "G5": "经验策略",
}

SHORT = {
    "product_manager": "产品经理",
    "project_manager": "项目经理",
    "ai_architect": "架构师",
    "develop": "Develop",
    "devops": "DevOps",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_base_packs(pack_ids: list[str]) -> dict:
    """从 genome-packs.js 用 node+vm 抽出指定 pack（避免手写解析）。"""
    script = r"""
const fs = require('fs');
const vm = require('vm');
const ids = JSON.parse(process.argv[1]);
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync('genome-packs.js', 'utf8'), ctx);
const packs = ctx.window.YIAGENT_GENOME_PACKS || {};
const out = {};
for (const id of ids) {
  if (!packs[id]) throw new Error('missing pack ' + id);
  out[id] = packs[id];
}
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", script, json.dumps(pack_ids)],
        cwd=str(CONSOLE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"load base packs failed: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def _allele_count(alleles: dict) -> int:
    return sum(len(v or []) for v in alleles.values())


def _dim_labels(blueprint: dict) -> list[str]:
    dims = blueprint.get("dimensions") or []
    out = []
    for d in dims:
        if not isinstance(d, dict):
            continue
        label = (
            d.get("id")
            or d.get("name")
            or d.get("label")
            or d.get("title")
            or d.get("key")
        )
        if label:
            out.append(str(label))
    return out


def _build_v11_pack(seat: str, base_id: str, base_pack: dict, genome: dict) -> tuple[dict, dict]:
    src = genome.get("source") or {}
    run_id = src.get("run_id")
    if not run_id:
        raise RuntimeError(f"{seat}: genome.json missing source.run_id")
    report_path = RUNS / run_id / "report.json"
    if not report_path.is_file():
        raise RuntimeError(f"{seat}: missing report {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    bank = report.get("bank") or {}
    dims = _dim_labels(report.get("blueprint") or {})
    champ_slots = genome.get("slots") or {}

    # 1) 原 pack 全量
    alleles: dict[str, list] = {}
    base_alleles = (base_pack.get("alleles") or {})
    for slot in ("G1", "G2", "G3", "G4", "G5"):
        alleles[slot] = [copy.deepcopy(a) for a in (base_alleles.get(slot) or [])]

    # 2) factory bank 全量
    seen: dict[str, set[str]] = {s: {a.get("id") for a in alleles[s] if a.get("id")} for s in alleles}
    factory_added = 0
    for slot in ("G1", "G2", "G3", "G4", "G5"):
        champ = champ_slots.get(slot) or {}
        champ_aid = champ.get("allele_id")
        champ_in_bank = False
        for raw in bank.get(slot) or []:
            aid = raw.get("id") or "unknown"
            fid = f"factory.{slot.lower()}.{aid}"
            if fid in seen[slot]:
                continue
            is_champ = bool(champ_aid and aid == champ_aid)
            if is_champ:
                champ_in_bank = True
            strength = raw.get("strength") or ""
            label = raw.get("label") or SLOT_LABEL[slot]
            if is_champ:
                label = f"★ {label}"
            text_parts = [
                (raw.get("text") or "").strip(),
                f"strength: {strength}" if strength else "",
                f"hypothesis: {raw.get('hypothesis')}" if raw.get("hypothesis") else "",
                f"source: rolefactory/{run_id} · seat={seat} · bank · v1.1"
                + (" · champion" if is_champ else ""),
            ]
            alleles[slot].append(
                {
                    "id": fid,
                    "label": label,
                    "active": True,
                    "version": "1.1",
                    "strength": strength,
                    "champion": is_champ,
                    "mean": src.get("champion_weighted") if is_champ else None,
                    "text": "\n".join(p for p in text_parts if p),
                }
            )
            seen[slot].add(fid)
            factory_added += 1

        # bank 未含冠军时，用 runtime genome 补一条
        if champ.get("text") and not champ_in_bank:
            fid = f"factory.{slot.lower()}.{(champ_aid or 'champ')}.runtime"
            if fid not in seen[slot]:
                alleles[slot].append(
                    {
                        "id": fid,
                        "label": f"★ {champ.get('allele_label') or SLOT_LABEL[slot]}",
                        "active": True,
                        "version": "1.1",
                        "champion": True,
                        "mean": src.get("champion_weighted"),
                        "text": (
                            f"{champ.get('text')}\n"
                            f"source: rolefactory/{run_id} · seat={seat} · runtime champion · v1.1"
                        ),
                    }
                )
                seen[slot].add(fid)
                factory_added += 1

    short = SHORT[base_id]
    pack_id = f"{base_id}_v1_1"
    n_base = _allele_count(base_alleles)
    n_total = _allele_count(alleles)
    pack = {
        "id": pack_id,
        "base_pack": base_id,
        "version": "1.1",
        "title": f"{short} v1.1（原库+factory）",
        "short": f"{short} v1.1",
        "note": (
            f"同角色 v1.1 · 不替换 `{base_id}` · "
            f"原库 {n_base} 等位 + factory bank {factory_added} · 合计 {n_total} · "
            f"run `{run_id}` · 冠军 {src.get('champion_weighted')} · "
            f"Δ{src.get('delta_train_weighted')} · "
            f"评测维 {len(dims)}：{' / '.join(dims) if dims else '—'}"
        ),
        "casePerf": (
            f"objective · 冠军 {src.get('champion_weighted')} · "
            f"Δ{src.get('delta_train_weighted')} · 评测维×{len(dims)}"
        ),
        "dimensions": dims,
        "factory": {
            "seat": seat,
            "run_id": run_id,
            "champion_weighted": src.get("champion_weighted"),
            "delta_train_weighted": src.get("delta_train_weighted"),
            "same_role_as": base_id,
            "allele_counts": {
                "base": n_base,
                "factory_added": factory_added,
                "total": n_total,
                "by_slot": {s: len(alleles[s]) for s in alleles},
            },
        },
        "alleles": alleles,
    }
    meta = {
        "seat": seat,
        "base_pack": base_id,
        "pack_id": pack_id,
        "run_id": run_id,
        "alleles_base": n_base,
        "alleles_factory_added": factory_added,
        "alleles_total": n_total,
        "dimensions": dims,
    }
    return pack, meta


def main() -> int:
    base_ids = list(SEAT_TO_PACK.values())
    base_packs = _load_base_packs(base_ids)
    packs: dict = {}
    rows = []
    for seat, base_id in SEAT_TO_PACK.items():
        genome = json.loads((RUNTIME / seat / "genome.json").read_text(encoding="utf-8"))
        pack, meta = _build_v11_pack(seat, base_id, base_packs[base_id], genome)
        packs[pack["id"]] = pack
        rows.append(meta)

    lines = [
        "/**",
        " * 基因组工作台 · 同角色 v1.1（增量加厚，不覆盖原 pack）",
        f" * generated {_now()}",
        " * 组成：原 pack 全量等位 + rolefactory bank 全量等位；原 product_manager / … 不动。",
        " */",
        "(function () {",
        "  const PACKS = (window.YIAGENT_GENOME_PACKS = window.YIAGENT_GENOME_PACKS || {});",
        f"  const V11 = {json.dumps(packs, ensure_ascii=False, indent=2)};",
        "  Object.keys(V11).forEach((id) => {",
        "    // 绝不改写 base pack；仅写入 *_v1_1",
        "    PACKS[id] = V11[id];",
        "  });",
        "  Object.keys(PACKS).forEach((id) => {",
        "    if (/_v1_0$/.test(id)) delete PACKS[id];",
        "  });",
        f"  window.YIAGENT_GENOME_V11 = {{ synced_at: {_now()!r}, packs: Object.keys(V11), mode: 'additive_enriched' }};",
        "})();",
        "",
    ]
    OUT_JS.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(
        json.dumps(
            {"synced_at": _now(), "mode": "additive_enriched", "seats": rows},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    DOC.write_text(
        "\n".join(
            [
                "# 基因组工作台 · 同角色 v1.1（增量加厚）",
                "",
                f"- 同步：{_now()}",
                "- **模式：只新增 `*_v1_1`，不删除、不覆盖原基因组 pack**",
                "- **加厚**：原 pack 全量等位基因 + 该席 `report.bank` 全部等位（含 weak/strong）+ 冠军标记",
                "- **评测维**：写入 pack.`dimensions`（blueprint；槽位仍为 G1–G5）",
                "- 文件：`YiAgent/console/genome-packs-factory-v11.js`",
                "",
                "| 席位 | 原 pack | v1.1 pack | 原库等位 | +factory | 合计 | 评测维 |",
                "|------|---------|-----------|----------|---------|------|--------|",
                *[
                    (
                        f"| {r['seat']} | `{r['base_pack']}` | `{r['pack_id']}` | "
                        f"{r['alleles_base']} | {r['alleles_factory_added']} | {r['alleles_total']} | "
                        f"{len(r.get('dimensions') or [])} |"
                    )
                    for r in rows
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("wrote", OUT_JS)
    for r in rows:
        print(
            f"  {r['seat']}: {r['alleles_base']}+{r['alleles_factory_added']}={r['alleles_total']} "
            f"dims={len(r.get('dimensions') or [])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
