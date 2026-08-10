#!/usr/bin/env python3
"""证据链对账：一条命令把「实跑 → 交付实体」五处产物核成一致。

目标 A 宣称的是「**可复现证据** + gene hash 可加载交付」。可复现的前提是证据自洽，
而证据现在散在五处，各自都能被单独改动：

    report.json        工厂实跑原始记录（不可变）
    genome_card.json   基因组卡：逐槽文本哈希 + 判定
    genome.json        席位落盘基因组（bridge / 控制台读这个）
    <席位>.bank.json   yiagent 格式基因库（装配吃这个）
    vector.json        表达载体（Agent 实体真正跑的那份）

任何一处被手改、或某一步忘了重跑，链条就断了 —— 而**断了不会有任何报错**：
基因照样装配、Agent 照样启动，只是它宣称的战绩不再对应它实际带的基因。
这个脚本就是来让「断了」变成一条非零退出码。

核的是六件事（逐席）：

1. 槽位文本：卡片的 `text_sha256` 必须等于 genome.json / bank / 载体里实际那段文本的哈希
2. 基因哈希：卡片 / genome.json / bank 冠军 variant / 载体 `markers.gene_hash` 四处相同
3. 判定：卡片 / genome.json / bank / 载体四处的 `generalizes` 与标签相同
4. 宣称纪律：未证明泛化（`generalizes is not True`）时，`claim` 里不许出现「更强」
5. 对照件：全弱 variant 必须自带血统且 `generalizes` 不为真（不许继承冠军战绩）
6. 载体来源路径可移植：`markers.source.path` 不能是绝对路径（换机器就不可复现）

用法：
    python scripts/verify_chain.py              # 六席全核，有问题退出码 1
    python scripts/verify_chain.py --seat PM
    python scripts/verify_chain.py --json       # 机器可读
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "rolefactory" / "tools"))

SEATS = ("Product", "PM", "Architect", "Dev", "DevOps", "Evals")
SLOTS = ("G1", "G2", "G3", "G4", "G5")
DEVELOP = REPO / "console" / "_workbench" / "AgentTeam" / "Develop"
BANKS = REPO / "rolefactory" / "data" / "yiagent_banks"
RUNS = REPO / "rolefactory" / "data" / "runs"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 缺文件/坏 JSON 都当「这一环不存在」，由调用方记问题
        return None


def verdict_of(obj: Any) -> tuple[Any, str]:
    """取出 (generalizes, 标签)。三处结构不同但都把判定放在 verdict 下。"""
    v = (obj or {}).get("verdict") or {}
    g = v.get("generalizes")
    return (g if isinstance(g, bool) else None), str(v.get("label") or "")


def check_seat(seat: str) -> dict[str, Any]:
    problems: list[str] = []
    seat_dir = DEVELOP / seat
    genome = load(seat_dir / "genome.json")
    vector = load(seat_dir / "vector.json")
    bank = load(BANKS / f"{seat}.bank.json")

    if genome is None:
        return {"seat": seat, "ok": False, "problems": ["缺 genome.json"], "run_id": None}

    src = genome.get("source") or {}
    run_id = str(src.get("run_id") or "")
    card = load(RUNS / run_id / "genome_card.json") if run_id else None
    report = load(RUNS / run_id / "report.json") if run_id else None

    if not run_id:
        problems.append("genome.json 缺 source.run_id：无法回溯到实跑")
    if report is None:
        problems.append(f"缺 report.json（run {run_id}）：实跑原始记录不在库里")
    if card is None:
        problems.append(f"缺 genome_card.json（run {run_id}）")
    if bank is None:
        problems.append(f"缺 {seat}.bank.json")
    if vector is None:
        problems.append("缺 vector.json：没有可运行实体")

    # ---- 1) 槽位文本哈希：卡片 vs genome.json ----
    g_slots = genome.get("slots") or {}
    if card:
        for slot in SLOTS:
            want = (card.get("slots") or {}).get(slot) or {}
            got = g_slots.get(slot) or {}
            if want.get("allele_id") != got.get("allele_id"):
                problems.append(
                    f"{slot} 等位不一致：卡片 {want.get('allele_id')} vs 基因组 {got.get('allele_id')}"
                )
            if want.get("text_sha256") and sha256(str(got.get("text") or "")) != want["text_sha256"]:
                problems.append(f"{slot} 文本哈希不一致（基因组被改过或卡片过期）")

    # ---- 1b) bank 与载体带的是不是同一段文本 ----
    champ = None
    if bank:
        champ = next(
            (v for v in bank.get("variants") or [] if str(v.get("id", "")).endswith(".champion")),
            None,
        )
        if champ is None:
            problems.append("bank 里没有 champion variant")
        else:
            by_id = {
                a.get("id"): a for slot in SLOTS for a in (bank.get("alleles") or {}).get(slot) or []
            }
            for slot in SLOTS:
                aid = (champ.get("slots") or {}).get(slot)
                text = str((by_id.get(aid) or {}).get("text") or "")
                g_text = str((g_slots.get(slot) or {}).get("text") or "")
                if aid != (g_slots.get(slot) or {}).get("allele_id"):
                    problems.append(f"{slot} 等位 id：bank {aid} vs 基因组 {(g_slots.get(slot) or {}).get('allele_id')}")
                elif text != g_text:
                    problems.append(f"{slot} 文本：bank 与基因组不同（同一 id 不同内容，最危险的一种漂移）")

    # ---- 2) 基因哈希四处一致 ----
    hashes = {
        "genome.json": str(src.get("genome_hash") or ""),
        "genome_card": str((card or {}).get("genome_hash") or ""),
        "bank.champion": str((champ or {}).get("hash") or ""),
        "vector": str(((vector or {}).get("markers") or {}).get("gene_hash") or ""),
    }
    present = {k: v for k, v in hashes.items() if v}
    if not present:
        problems.append("四处都没有 gene hash：交付无法对账")
    elif len(set(present.values())) > 1:
        problems.append("gene hash 不一致：" + "，".join(f"{k}={v[:12]}" for k, v in present.items()))
    for key, val in hashes.items():
        if not val:
            problems.append(f"{key} 缺 gene hash")

    # ---- 3) 判定四处一致 ----
    bank_pr = (bank or {}).get("meta", {}).get("provenance") or {}
    vec_pr = ((vector or {}).get("markers") or {}).get("provenance") or {}
    verdicts = {
        "genome.json": verdict_of(src),
        "genome_card": verdict_of(card or {}),
        "bank": verdict_of(bank_pr),
        "vector": verdict_of(vec_pr),
    }
    seen = {k: v for k, v in verdicts.items() if v[1]}
    if not seen:
        problems.append("四处都没有泛化判定：无法知道能不能宣称更强")
    elif len({v[0] for v in seen.values()}) > 1 or len({v[1] for v in seen.values()}) > 1:
        problems.append(
            "判定不一致：" + "，".join(f"{k}={v[0]}/{v[1]}" for k, v in seen.items())
        )

    # ---- 4) 宣称纪律 ----
    proven = verdicts["vector"][0] if vec_pr else verdicts["genome.json"][0]
    for name, pr in (("bank", bank_pr), ("vector", vec_pr)):
        claim = str(pr.get("claim") or "")
        if pr and not claim:
            problems.append(f"{name} 血统缺 claim：没写清能对外说什么")
        if proven is not True and "更强" in claim and "不得" not in claim:
            problems.append(f"{name} 未证明泛化却宣称更强：{claim}")

    # ---- 5) 对照件不许继承战绩 ----
    if bank:
        weak = next(
            (v for v in bank.get("variants") or [] if str(v.get("id", "")).endswith(".all_weak")),
            None,
        )
        if weak is not None:
            wpr = weak.get("provenance") or {}
            if not wpr:
                problems.append("全弱对照没自带血统：会继承冠军战绩")
            elif verdict_of(wpr)[0] is True:
                problems.append("全弱对照的判定为「已证明」：对照件不该有战绩")

    # ---- 6) 载体来源路径可移植 ----
    spath = str((((vector or {}).get("markers") or {}).get("source") or {}).get("path") or "")
    if spath and (spath[1:3] == ":\\" or spath.startswith("/")):
        problems.append(f"载体来源是绝对路径，换机器不可复现：{spath}")

    return {
        "seat": seat,
        "ok": not problems,
        "run_id": run_id or None,
        "gene_hash": (next(iter(present.values()))[:16] if present else None),
        "verdict": verdicts["genome.json"][1] or None,
        "generalizes": proven,
        "problems": problems,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="实跑 → 交付实体 证据链对账")
    ap.add_argument("--seat", action="append", default=[], help="只核某席（可重复）")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    seats = args.seat or list(SEATS)
    rows = [check_seat(s) for s in seats]

    if args.as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"证据链对账 · {len(rows)} 席\n")
        for r in rows:
            mark = "ok  " if r["ok"] else "**断**"
            print(
                f"  {r['seat']:<10} {mark} run={r['run_id'] or '-'}"
                f" hash={r['gene_hash'] or '-'} 判定={r['verdict'] or '-'}"
            )
            for p in r["problems"]:
                print(f"      · {p}")
        bad = [r for r in rows if not r["ok"]]
        print(
            f"\n{len(rows) - len(bad)}/{len(rows)} 席证据自洽。"
            + ("" if not bad else f" 断链：{', '.join(r['seat'] for r in bad)}")
        )
        proven = sum(1 for r in rows if r["generalizes"] is True)
        print(
            f"其中 {proven}/{len(rows)} 席**已证明**泛化 —— 自洽只说明「证据没被改坏」，"
            "不等于「基因更强」，后者看 holdout 区间。"
        )
    return 1 if any(not r["ok"] for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
