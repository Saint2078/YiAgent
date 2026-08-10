#!/usr/bin/env python3
"""基因组卡：把一次实跑的冠军基因组做成**可加载、可校验、可解释**的交付物。

产出（写进 `data/runs/<run_id>/`）：
- `genome_card.json`：冠军等位 + 内容哈希 + 逐槽消融贡献 + holdout 配对 + 复现配方
- `genome_card.md`：同内容的人读版

内容哈希 `genome_hash` 只由「role_id + 每槽 allele_id + 槽文本 sha256」决定，
不含分数与时间戳：同一套基因文本在任何机器上算出同一个 hash，可用于加载校验。

用法：
    python tools/genome_card.py <run_id> [run_id ...]     # 生成卡
    python tools/genome_card.py verify <run_id> <genome.json>   # 校验落盘基因组是否与卡一致
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]
RUNS = HERE / "data" / "runs"
SLOTS = ("G1", "G2", "G3", "G4", "G5")
SLOT_LABEL = {
    "G1": "身份",
    "G2": "人设与决策边界",
    "G3": "知识",
    "G4": "能力与工具",
    "G5": "经验策略",
}


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _read_report(run_id: str) -> dict[str, Any]:
    p = RUNS / run_id / "report.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing report: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def allele_of(bank: dict[str, Any], slot: str, allele_id: str | None) -> dict[str, Any]:
    for a in bank.get(slot) or []:
        if a.get("id") == allele_id:
            return a
    return {}


def genome_slots(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bank = report.get("bank") or {}
    cg = report.get("champion_genome") or {}
    choice = cg.get("choice") or {}
    labels = cg.get("labels") or {}
    out: dict[str, dict[str, Any]] = {}
    for slot in SLOTS:
        aid = choice.get(slot)
        a = allele_of(bank, slot, aid)
        text = str(a.get("text") or "")
        out[slot] = {
            "slot_label": SLOT_LABEL[slot],
            "allele_id": aid,
            "allele_label": labels.get(slot) or a.get("label"),
            "strength": a.get("strength"),
            "hypothesis": a.get("hypothesis"),
            "text": text,
            "text_sha256": _sha256(text),
            "text_chars": len(text),
        }
    return out


def genome_hash(role_id: str, slots: dict[str, dict[str, Any]]) -> str:
    canon = {
        "role_id": role_id,
        "slots": {
            s: {"allele_id": slots[s]["allele_id"], "text_sha256": slots[s]["text_sha256"]}
            for s in SLOTS
        },
    }
    return _sha256(json.dumps(canon, ensure_ascii=False, sort_keys=True))


def ablation(report: dict[str, Any]) -> dict[str, Any]:
    """逐槽贡献：第 0 代 all_strong 与 ablate_Gx（该槽换成弱等位）的加权分差。

    正值 = 该槽的强等位有贡献；负值 = 强等位反而拖分（真实会发生，不修饰）。
    """
    gens = report.get("generations") or []
    gen0 = next((g for g in gens if g.get("gen") == 0), None)
    if not gen0:
        return {"available": False, "reason": "无第 0 代记录"}
    variants = gen0.get("variants") or []
    full = next((v for v in variants if v.get("origin") == "all_strong"), None)
    if not full:
        return {"available": False, "reason": "第 0 代无 all_strong 参照臂"}
    rows = []
    for slot in SLOTS:
        ab = next((v for v in variants if v.get("origin") == f"ablate_{slot}"), None)
        if not ab:
            continue
        d_w = round(float(full.get("weighted") or 0) - float(ab.get("weighted") or 0), 2)
        d_c = round(float(full.get("composite") or 0) - float(ab.get("composite") or 0), 2)
        rows.append(
            {
                "slot": slot,
                "slot_label": SLOT_LABEL[slot],
                "full_weighted": full.get("weighted"),
                "ablated_weighted": ab.get("weighted"),
                "delta_weighted": d_w,
                "delta_composite": d_c,
            }
        )
    rows.sort(key=lambda r: -r["delta_weighted"])
    return {
        "available": bool(rows),
        "reference_arm": {"id": full.get("id"), "weighted": full.get("weighted")},
        "by_slot": rows,
        "note": (
            "消融只换一个槽为弱等位，其余保持强等位；单次采样、样本量小，"
            "只读排序与量级，不做显著性声明。"
        ),
    }


def verdict(scores: dict[str, Any], hold: dict[str, Any]) -> dict[str, Any]:
    """泛化判定：train 上赢不算数，只看 holdout 的配对差值。

    判定优先级：**有置信区间就以区间为准**（区间跨 0 = 判不了，不许当赢）；
    旧 run 的报告没有区间，退回「Δ 符号 + 升降计数」的粗判，并在 reason 里注明。
    """
    d = hold.get("delta_weighted")
    paired = hold.get("paired") or {}
    n = int(paired.get("cases") or 0)
    imp = int(paired.get("improved") or 0)
    reg = int(paired.get("regressed") or 0)
    reps = hold.get("reps")
    if d is None or not n:
        return {"generalizes": None, "label": "未鉴定", "reason": "无 holdout 结果"}

    ci = paired.get("mean_delta_ci95")
    sample = f"n={n} 题" + (f" × {reps} 次" if reps else "")
    if ci:
        lo, hi = ci[0], ci[1]
        band = f"配对Δ均值={paired.get('mean_delta'):+} 95%CI[{lo:+}, {hi:+}]（{sample}）"
        if lo > 0:
            return {"generalizes": True, "label": "holdout 站得住",
                    "reason": f"{band}：区间整体在 0 以上"}
        if hi < 0:
            return {"generalizes": False, "label": "未通过泛化鉴定",
                    "reason": (f"{band}：区间整体在 0 以下，"
                               f"train 增益（{scores.get('delta_train_weighted')}）是过拟合")}
        return {"generalizes": None, "label": "判不了（区间跨 0）",
                "reason": f"{band}：换一组题就可能翻符号，需加题量或重复次数"}

    note = "（该 run 无置信区间，粗判）"
    if d > 0 and imp > reg:
        return {"generalizes": True, "label": "holdout 站得住",
                "reason": f"holdout Δ={d:+}，配对 {imp} 升 / {reg} 降（{sample}）{note}"}
    if d <= 0:
        return {"generalizes": False, "label": "未通过泛化鉴定",
                "reason": (f"holdout Δ={d:+}，配对 {imp} 升 / {reg} 降（{sample}）："
                           f"train 上的增益（{scores.get('delta_train_weighted')}）大概率是过拟合，"
                           f"不能宣称该基因组更强{note}")}
    return {"generalizes": None, "label": "证据不足",
            "reason": f"holdout Δ={d:+} 但配对 {imp} 升 / {reg} 降（{sample}），方向不一致{note}"}


def build_card(run_id: str) -> dict[str, Any]:
    report = _read_report(run_id)
    role_id = str(report.get("role_id") or "")
    slots = genome_slots(report)
    scores = report.get("scores") or {}
    champ = scores.get("champion_train") or {}
    base = scores.get("baseline_no_genes") or {}
    weak = scores.get("all_weak_genes") or {}
    hold = scores.get("holdout") or {}
    perf = report.get("performance") or {}
    params = report.get("params") or {}
    missing = [s for s in SLOTS if not slots[s]["text"]]
    return {
        "schema": "yiagent.rolefactory.genome_card/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": report.get("run_id"),
        "role": report.get("role"),
        "role_id": role_id,
        "status": report.get("status"),
        "genome_hash": genome_hash(role_id, slots),
        "loadable": not missing,
        "missing_slots": missing,
        "slots": slots,
        "system_prompt": (report.get("champion_genome") or {}).get("system"),
        "scoring": {
            "mode": (report.get("scoring") or {}).get("mode"),
            "how": (report.get("scoring") or {}).get("how"),
            "check_types": (report.get("scoring") or {}).get("check_types"),
            "verified_cases": (report.get("scoring") or {}).get("verified_cases"),
        },
        "scores": {
            "baseline_no_genes_weighted": base.get("weighted"),
            "all_weak_weighted": weak.get("weighted"),
            "champion_train_weighted": champ.get("weighted"),
            "delta_train_weighted": scores.get("delta_train_weighted"),
            "paired_train": scores.get("paired_train"),
            "holdout_champion_weighted": (hold.get("champion") or {}).get("weighted"),
            "holdout_baseline_weighted": (hold.get("baseline") or {}).get("weighted"),
            "holdout_delta_weighted": hold.get("delta_weighted"),
            "holdout_paired": hold.get("paired"),
            "generalization_gap": hold.get("generalization_gap"),
        },
        "verdict": verdict({**scores}, hold),
        "ablation": ablation(report),
        "suite": report.get("suite"),
        "reproduce": {
            "service": "rolefactory (Docker, 127.0.0.1:8790)",
            "endpoint": "POST /api/run",
            "params": params,
            "note": (
                "同一 seed 复现的是搜索路径（种群与配对），不是逐字回答："
                "LLM 采样有随机性。判分是纯 Python 断言，对同一份回答任何时候复算同分。"
            ),
            "verify_command": f"python tools/genome_card.py verify {report.get('run_id')} <genome.json>",
        },
        "performance": {
            "wall_seconds": report.get("wall_seconds"),
            "phase_seconds": perf.get("phase_seconds"),
            "parallel": perf.get("parallel"),
            "tokens_per_eval": perf.get("tokens_per_eval"),
            "evals": perf.get("evals"),
        },
        "caveats": report.get("caveats"),
    }


def card_md(card: dict[str, Any]) -> str:
    s = card["slots"]
    sc = card["scores"]
    ab = card.get("ablation") or {}
    lines = [
        f"# 基因组卡 · {card.get('role')}（run `{card.get('run_id')}`）",
        "",
        "| 项 | 值 |",
        "|----|-----|",
        f"| role_id | `{card.get('role_id')}` |",
        f"| genome_hash | `{card.get('genome_hash')}` |",
        f"| 可加载 | {'是' if card.get('loadable') else '否：缺 ' + '/'.join(card.get('missing_slots') or [])} |",
        f"| **泛化鉴定** | **{(card.get('verdict') or {}).get('label')}** —— {(card.get('verdict') or {}).get('reason')} |",
        f"| 判分 | {(card.get('scoring') or {}).get('mode')} |",
        f"| 自校通过题数 | {(card.get('scoring') or {}).get('verified_cases')} |",
        f"| 冠军(train) | {sc.get('champion_train_weighted')} |",
        f"| 基线(无基因) | {sc.get('baseline_no_genes_weighted')} |",
        f"| 全弱基因 | {sc.get('all_weak_weighted')} |",
        f"| Δ(train) | {sc.get('delta_train_weighted')} |",
        f"| holdout 冠军 / 基线 / Δ | {sc.get('holdout_champion_weighted')} / "
        f"{sc.get('holdout_baseline_weighted')} / {sc.get('holdout_delta_weighted')} |",
        f"| 泛化差(train−holdout) | {sc.get('generalization_gap')} |",
        "",
        "## 冠军等位",
        "",
        "| 槽 | 含义 | 等位 | 标签 | 强弱 | 文本 sha256（前 12） |",
        "|----|------|------|------|------|----------------------|",
    ]
    for slot in SLOTS:
        row = s[slot]
        lines.append(
            f"| {slot} | {row['slot_label']} | `{row['allele_id']}` | {row['allele_label']} | "
            f"{row.get('strength') or '—'} | `{row['text_sha256'][:12]}` |"
        )
    lines += ["", "## 逐槽消融贡献（all_strong − ablate_slot）", ""]
    if ab.get("available"):
        lines += [
            "| 槽 | 含义 | 全强 | 换弱 | Δ加权 | Δcomposite |",
            "|----|------|------|------|-------|------------|",
        ]
        for r in ab["by_slot"]:
            lines.append(
                f"| {r['slot']} | {r['slot_label']} | {r['full_weighted']} | {r['ablated_weighted']} | "
                f"{r['delta_weighted']:+} | {r['delta_composite']:+} |"
            )
        lines += ["", f"> {ab.get('note')}"]
    else:
        lines.append(f"（不可用：{ab.get('reason')}）")

    rep = card.get("reproduce") or {}
    perf = card.get("performance") or {}
    par = perf.get("parallel") or {}
    lines += [
        "",
        "## 复现",
        "",
        f"- 服务：{rep.get('service')} · `{rep.get('endpoint')}`",
        f"- 参数：`{json.dumps(rep.get('params') or {}, ensure_ascii=False)}`",
        f"- 校验：`{rep.get('verify_command')}`",
        f"- {rep.get('note')}",
        "",
        "## 性能",
        "",
        f"- 墙钟 {perf.get('wall_seconds')}s · 每评测 tokens {perf.get('tokens_per_eval')}",
        f"- 阶段耗时：`{json.dumps(perf.get('phase_seconds') or {}, ensure_ascii=False)}`",
        f"- 真实并行 {par.get('effective_parallel')} / 上限 {par.get('concurrency_cap')}"
        f"（利用率 {par.get('utilization_vs_cap')}）· 长尾对冲 {par.get('hedges')} 次",
        "",
        "## 已知局限",
        "",
    ]
    for c in card.get("caveats") or []:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def write_card(run_id: str) -> dict[str, Any]:
    card = build_card(run_id)
    d = RUNS / run_id
    (d / "genome_card.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (d / "genome_card.md").write_text(card_md(card), encoding="utf-8")
    print(
        f"{run_id} · {card.get('role')} · hash={card['genome_hash'][:16]} "
        f"loadable={card['loadable']} champ={card['scores'].get('champion_train_weighted')}"
    )
    return card


def verify(run_id: str, genome_path: Path) -> int:
    """校验落盘 genome.json 与卡一致：逐槽文本 sha256 与整体 hash 都要对得上。"""
    card = build_card(run_id)
    g = json.loads(genome_path.read_text(encoding="utf-8"))
    slots = g.get("slots") or {}
    problems: list[str] = []
    rebuilt: dict[str, dict[str, Any]] = {}
    for slot in SLOTS:
        want = card["slots"][slot]
        got = slots.get(slot) or {}
        got_text = str(got.get("text") or "")
        rebuilt[slot] = {
            "allele_id": got.get("allele_id"),
            "text_sha256": _sha256(got_text),
        }
        if got.get("allele_id") != want["allele_id"]:
            problems.append(f"{slot} allele_id: {got.get('allele_id')} != {want['allele_id']}")
        if _sha256(got_text) != want["text_sha256"]:
            problems.append(f"{slot} 文本 sha256 不一致（{len(got_text)} 字）")
    got_hash = _sha256(
        json.dumps(
            {"role_id": card["role_id"], "slots": {s: rebuilt[s] for s in SLOTS}},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    same = got_hash == card["genome_hash"]
    print(f"run={run_id} file={genome_path}")
    print(f"  card hash = {card['genome_hash']}")
    print(f"  file hash = {got_hash}")
    if same and not problems:
        print("  VERIFIED 一致：该基因组即本次实跑的冠军，可加载")
        return 0
    print("  MISMATCH")
    for p in problems:
        print(f"   - {p}")
    return 1


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "verify":
        if len(args) < 3:
            print("用法：genome_card.py verify <run_id> <genome.json>", file=sys.stderr)
            return 2
        return verify(args[1], Path(args[2]))
    rc = 0
    for run_id in args:
        try:
            write_card(run_id)
        except Exception as exc:  # noqa: BLE001
            print(f"{run_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
