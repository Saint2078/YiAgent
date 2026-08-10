#!/usr/bin/env python3
"""把一次 rolefactory 实跑导出成 `yiagent` 能装配的基因库（bank）。

存在的理由：两条链路格式不同，此前接不上 ——

- rolefactory 产出 `bank[G1] = [{id,label,text,strength,...}]` + `champion.choice{G1: 等位id}`
- `yiagent assemble` 吃 `alleles[G1] = [...]` + `variants[].slots{G1: 等位id}`

于是「六席实跑冠军」一直没有对应的可运行 Agent 实体。本工具补这一段，产物是普通
bank JSON，`yiagent assemble` 直接可用，两边**不产生代码依赖**。

关键约定：`variant.hash` 写的是**基因组卡的规范哈希**（64 位 sha256，只由
role_id + 每槽 allele_id + 槽文本决定）。因此表达载体里的 `markers.gene_hash`
可以一路回溯到工厂那次实跑，用 `genome_card.py verify` 对账。

同时把泛化判定放进 `meta.provenance`：一份 holdout「判不了」的基因，装出来的实体
必须自带这句话，不能看起来跟已验证的一样。

用法：
    python tools/export_yiagent_bank.py <run_id> [--out 路径] [--all]
    python tools/export_yiagent_bank.py --seat PM        # 按席位取现役 run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS = ROOT / "data" / "runs"
SLOTS = ("G1", "G2", "G3", "G4", "G5")
# 与 build_devteam.py 的 TEAM 对应；只用于 --seat 便捷查找
SEAT_DIRS = ROOT.parent / "console" / "_workbench" / "AgentTeam" / "Develop"

sys.path.insert(0, str(HERE))
from genome_card import SLOT_LABEL, build_card  # noqa: E402


def _read_report(run_id: str) -> dict[str, Any]:
    p = RUNS / run_id / "report.json"
    if not p.is_file():
        raise SystemExit(f"找不到报告：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _seat_run_id(seat: str) -> str:
    p = SEAT_DIRS / seat / "genome.json"
    if not p.is_file():
        raise SystemExit(f"席位 {seat} 没有落盘基因组：{p}")
    rid = ((json.loads(p.read_text(encoding="utf-8")).get("source") or {}).get("run_id")) or ""
    if not rid:
        raise SystemExit(f"席位 {seat} 的基因组没有 source.run_id")
    return str(rid)


def alleles_of(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """工厂基因库 → yiagent alleles。保留 strength / hypothesis：
    做消融或再进化时还用得上，装配侧只读 id/label/text，多余字段无害。"""
    bank = report.get("bank") or {}
    out: dict[str, list[dict[str, Any]]] = {}
    for slot in SLOTS:
        items = []
        for a in bank.get(slot) or []:
            if not (a.get("id") and str(a.get("text") or "").strip()):
                continue
            items.append(
                {
                    "id": str(a["id"]),
                    "label": a.get("label") or str(a["id"]),
                    "text": str(a["text"]),
                    "strength": a.get("strength"),
                    "hypothesis": a.get("hypothesis"),
                    "slot_name": a.get("slot_name") or SLOT_LABEL.get(slot),
                }
            )
        out[slot] = items
    return out


def claim_of(verdict: dict[str, Any]) -> str:
    """这份基因**允许对外说什么**。判定不成立时不许出现「更强 / 已验证」字样。"""
    g = verdict.get("generalizes")
    if g is True:
        return "可称『在未见题上优于无基因基线』（holdout 配对区间整体为正）"
    if g is False:
        return "不得称更强：holdout 配对区间整体为负，train 增益系过拟合"
    return (
        "不得称更强：holdout 未能判定（区间跨 0 或采样不足）。"
        "可称『由实跑冠军基因装配』，不可称『已验证更强』"
    )


def _run_at(report: dict[str, Any]) -> str:
    """实跑起始时刻（UTC ISO）。report 只存 epoch 秒，这里转成人能读、机器能对的形式。"""
    ts = report.get("created_at")
    if not isinstance(ts, (int, float)):
        return ""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def provenance_of(report: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    scores = report.get("scores") or {}
    hold = scores.get("holdout") or {}
    cs = card.get("scores") or {}
    verdict = card.get("verdict") or {}
    return {
        "factory": "rolefactory",
        "run_id": report.get("run_id"),
        "role": report.get("role"),
        "role_id": report.get("role_id"),
        "scoring_mode": (report.get("params") or {}).get("scoring_mode"),
        "genome_hash": card.get("genome_hash"),
        "champion_weighted": (scores.get("champion_train") or {}).get("weighted"),
        "baseline_weighted": (scores.get("baseline_no_genes") or {}).get("weighted"),
        "delta_train_weighted": scores.get("delta_train_weighted"),
        "holdout": {
            "source": cs.get("holdout_source") or "run",
            "reps": hold.get("reps") or 1,
            "delta_weighted": cs.get("holdout_delta_weighted"),
            "paired": cs.get("holdout_paired"),
        },
        "verdict": verdict,
        # 这条是给人看的：任何消费方复制载体时，把「能说什么」一起带走
        "claim": claim_of(verdict),
        "report": f"rolefactory/data/runs/{report.get('run_id')}/report.json",
        "genome_card": f"rolefactory/data/runs/{report.get('run_id')}/genome_card.md",
        "verify": f"python tools/genome_card.py verify {report.get('run_id')} <genome.json>",
        # 只记实跑时刻，**不记导出时刻**：交付物要是「这次实跑」的纯函数。
        # 一个 exported_at 就能让同一个 run 每次导出都换字节，下游载体跟着换，
        # 「可复现交付」当场变成空话；而「什么时候导的」git 历史里本来就有。
        "run_at": _run_at(report),
    }


def build_bank(run_id: str) -> dict[str, Any]:
    report = _read_report(run_id)
    card = build_card(run_id)
    alleles = alleles_of(report)
    missing = [s for s in SLOTS if not alleles[s]]
    if missing:
        raise SystemExit(f"run {run_id} 的基因库缺槽 {missing}，无法导出")

    choice = (report.get("champion_genome") or {}).get("choice") or {}
    slots = {s: str(choice.get(s) or "") for s in SLOTS}
    empty = [s for s in SLOTS if not slots[s]]
    if empty:
        raise SystemExit(f"run {run_id} 的冠军缺槽 {empty}，无法导出")

    role_id = str(report.get("role_id") or "")
    role = str(report.get("role") or role_id)
    variants: list[dict[str, Any]] = [
        {
            "id": f"var.{role_id}.champion",
            # 与基因组卡同一套规范哈希：载体的 gene_hash 可回溯到这次实跑
            "hash": card.get("genome_hash"),
            "title": f"{role} · 实跑冠军（run {run_id}）",
            "slots": slots,
            "role_in_pack": "champion",
        }
    ]
    # 附一条全弱对照：同槽位结构、全部取 weak 等位。做「基因到底起没起作用」的
    # 直观对照时不必再回工厂，本地两个载体一跑就看得出来。
    weak = {s: next((a["id"] for a in alleles[s] if a.get("strength") == "weak"), "") for s in SLOTS}
    if all(weak.values()):
        variants.append(
            {
                "id": f"var.{role_id}.all_weak",
                "title": f"{role} · 全弱基因对照",
                "slots": weak,
                "role_in_pack": "contrast_all_weak",
                # 自带血统压掉库级血统：这不是冠军，不能继承冠军的判定与「可宣称」。
                # 装配侧 variant.provenance 优先，所以对照件不会冒充战绩。
                "provenance": {
                    "factory": "rolefactory",
                    "run_id": report.get("run_id"),
                    "role": role,
                    "kind": "contrast_all_weak",
                    "verdict": {
                        "generalizes": None,
                        "label": "对照件（不参与判定）",
                        "reason": "全部取弱等位，用于观感对照，不是被鉴定的冠军基因。",
                    },
                    "claim": "仅作全弱对照，不代表任何战绩；不得作为交付实体",
                    "run_at": _run_at(report),
                },
            }
        )

    return {
        "meta": {
            "role_id": role_id,
            "display_name": role,
            "task": (report.get("blueprint") or {}).get("one_line") or role,
            "note": (
                "由 rolefactory 实跑冠军导出，非手工种子。"
                "分数与判定见 meta.provenance；对外表述受 provenance.claim 约束。"
            ),
            "provenance": provenance_of(report, card),
        },
        "alleles": alleles,
        "variants": variants,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="rolefactory 实跑 → yiagent 基因库")
    ap.add_argument("run_id", nargs="?", help="rolefactory run_id")
    ap.add_argument("--seat", help="按 Develop 席位取其现役 run（Product/PM/Architect/Dev/DevOps/Evals）")
    ap.add_argument("--out", type=Path, help="输出路径（默认 data/runs/<run_id>/yiagent_bank.json）")
    ap.add_argument("--all", action="store_true", help="导出全部六席")
    args = ap.parse_args()

    if args.all:
        seats = ["Product", "PM", "Architect", "Dev", "DevOps", "Evals"]
        for seat in seats:
            try:
                rid = _seat_run_id(seat)
                bank = build_bank(rid)
            except SystemExit as exc:
                print(f"  SKIP {seat}: {exc}", flush=True)
                continue
            out = ROOT / "data" / "yiagent_banks" / f"{seat}.bank.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            pr = bank["meta"]["provenance"]
            print(
                f"  {seat:10} ← {rid}  hash={(pr.get('genome_hash') or '')[:16]}  "
                f"判定={(pr.get('verdict') or {}).get('label')}\n"
                f"             → {out}",
                flush=True,
            )
        return 0

    run_id = args.run_id or (_seat_run_id(args.seat) if args.seat else "")
    if not run_id:
        ap.error("给 run_id，或用 --seat / --all")
    bank = build_bank(run_id)
    # --seat 的默认落点与 --all 一致：席位的基因库属于**席位**，不属于某个 run 目录。
    # 先前 --seat 落在 run 目录，而 scripts/build_agent_entities.py 读的是 yiagent_banks/，
    # 于是「刷新」跑完了、旧文件还在原地被继续使用 —— 断了且不报错。
    out = args.out or (
        ROOT / "data" / "yiagent_banks" / f"{args.seat}.bank.json" if args.seat
        else RUNS / run_id / "yiagent_bank.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pr = bank["meta"]["provenance"]
    print(f"wrote {out}")
    print(f"  role={pr.get('role')} hash={pr.get('genome_hash')}")
    print(f"  判定={(pr.get('verdict') or {}).get('label')}")
    print(f"  claim={pr.get('claim')}")
    print(f"  下一步：yiagent assemble {out} --variant {bank['variants'][0]['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
