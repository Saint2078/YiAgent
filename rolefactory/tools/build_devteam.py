#!/usr/bin/env python3
"""通过 rolefactory 真实构建 Develop 五席，并同步到 console/_workbench 与 A002.工作台。"""
from __future__ import annotations

import json
import shutil
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RF = "http://127.0.0.1:8790"
HERE = Path(__file__).resolve().parents[1]  # rolefactory/
YIAGENT = HERE.parent  # YiAgent/
A002 = YIAGENT.parent  # A002.YiAgent/
RUNTIME_WB = YIAGENT / "console" / "_workbench" / "AgentTeam" / "Develop"
DOC_WB = A002 / "工作台" / "AgentTeam" / "Develop"
REG_PATH = A002 / "工作台" / "AgentTeam" / "devteam-registry.md"

SLOT_META = {
    "G1": ("identity", "身份"),
    "G2": ("persona", "人设与决策边界"),
    "G3": ("knowledge", "知识"),
    "G4": ("capability", "能力与工具"),
    "G5": ("experience", "经验策略"),
}

# seat = bridge DEVELOP_ROLES 名；factory_role = 喂给 rolefactory 的中文岗名
TEAM = [
    {
        "seat": "Product",
        "factory_role": "产品经理",
        "title": "产品 · 边界与优先级",
        "provider": "kimi",
    },
    {
        "seat": "PM",
        "factory_role": "项目经理",
        "title": "项目经理 · 节奏与阻塞",
        "provider": "kimi",
    },
    {
        "seat": "Architect",
        "factory_role": "AI软件架构师",
        "title": "AI 架构师 · 边界与可演进",
        "provider": "kimi",
    },
    {
        "seat": "Dev",
        "factory_role": "软件开发工程师",
        "title": "开发 · 实现与单测",
        "provider": "kimi",
    },
    {
        "seat": "DevOps",
        "factory_role": "DevOps工程师",
        "title": "DevOps · 容器与可运行",
        "provider": "kimi",
    },
    {
        "seat": "Evals",
        "factory_role": "评测工程师",
        "title": "Evals 专员 · 评测与门禁",
        "provider": "kimi",
    },
]

# 真实构建参数（客观判分；略收紧以控墙钟，仍走完整进化）
RUN_PARAMS: dict[str, Any] = {
    "scoring_mode": "objective",
    "judge_shadow": False,
    "per_dim": 2,
    "generations": 3,
    # 10 而非 5：受控对照（PERF.md §8）里变体数 5→12 使同相位评测数翻倍而墙钟只多 10.6%，
    # 32 并发本来闲着（利用率 0.23）。代价是 token 随变体数线性涨，靠 budget_tokens 兜住。
    "variants_per_gen": 10,
    "reps": 1,
    "elite": 2,
    "min_gain": 0.5,
    "patience": 1,
    "seed": 20260810,
    # 32 为实测甜点（见 rolefactory/PERF.md）：再高吞吐不涨而 429 重试骤增
    "concurrency": 32,
    "budget_tokens": 2_500_000,
    "budget_seconds": 2400,
    "anchor_limit": 5,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http(method: str, path: str, body: dict | None = None, timeout: float = 60) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        RF + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def start_run(factory_role: str) -> str:
    payload = {"role": factory_role, **RUN_PARAMS}
    out = _http("POST", "/api/run", payload)
    rid = out["run_id"]
    print(f"  started {rid} role={factory_role}", flush=True)
    return rid


def wait_run(run_id: str) -> dict[str, Any]:
    while True:
        st = _http("GET", f"/api/run/{run_id}", timeout=30)
        status = st.get("status")
        phase = st.get("phase") or st.get("status")
        prog = st.get("progress") or {}
        wall = st.get("wall_seconds")
        print(
            f"  [{run_id}] status={status} phase={phase} "
            f"eval={prog.get('eval_done')}/{prog.get('eval_total')} "
            f"failed={prog.get('eval_failed')} wall={wall}s "
            f"phases={prog.get('phase_seconds')}",
            flush=True,
        )
        if status in ("done", "error", "aborted", "failed"):
            if status != "done":
                raise RuntimeError(f"run_failed:{run_id}:{status}:{st.get('error') or st.get('abort_reason')}")
            return _http("GET", f"/api/run/{run_id}/report", timeout=60)
        time.sleep(20)


def allele_text(bank: dict, slot: str, allele_id: str | None) -> tuple[str, str]:
    rows = bank.get(slot) or []
    for a in rows:
        if a.get("id") == allele_id:
            return str(a.get("text") or ""), str(a.get("label") or allele_id or "")
    return "", allele_id or ""


def report_to_genome(seat: str, meta: dict, report: dict) -> dict[str, Any]:
    bank = report.get("bank") or {}
    cg = report.get("champion_genome") or {}
    choice = cg.get("choice") or {}
    labels = cg.get("labels") or {}
    scores = report.get("scores") or {}
    champ = scores.get("champion_train") or {}
    slots: dict[str, Any] = {}
    for slot, (key, label) in SLOT_META.items():
        text, alabel = allele_text(bank, slot, choice.get(slot))
        if not text and cg.get("system"):
            # 回退：从 system 块切
            marker = f"【{slot}"
            sys = cg["system"]
            if marker in sys:
                part = sys.split(marker, 1)[1]
                part = part.split("【G", 1)[0]
                # 去掉 " 身份定位】\n" 一类
                if "】" in part:
                    part = part.split("】", 1)[1]
                text = part.strip()
        slots[slot] = {
            "key": key,
            "label": label,
            "text": text,
            "allele_id": choice.get(slot),
            "allele_label": labels.get(slot) or alabel,
        }
    return {
        "schema": "opc.agentteam.genome",
        "version": "0.2",
        "role": seat,
        "developRole": seat,
        "display_name": seat,
        "title": meta["title"],
        "provider": meta.get("provider") or "kimi",
        "factory_role": meta["factory_role"],
        "system_prompt": cg.get("system") or "",
        "slots": slots,
        "source": {
            "factory": "rolefactory",
            "run_id": report.get("run_id"),
            "role_id": report.get("role_id"),
            "scoring_mode": (report.get("params") or {}).get("scoring_mode"),
            "champion_weighted": champ.get("weighted"),
            "baseline_weighted": (scores.get("baseline_no_genes") or {}).get("weighted"),
            "delta_train_weighted": scores.get("delta_train_weighted"),
            "holdout": scores.get("holdout"),
            "built_at": _now(),
            "params": report.get("params"),
        },
    }


def write_genome(seat: str, genome: dict) -> list[Path]:
    written: list[Path] = []
    for root in (RUNTIME_WB, DOC_WB):
        d = root / seat
        d.mkdir(parents=True, exist_ok=True)
        p = d / "genome.json"
        p.write_text(json.dumps(genome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # 附带报告指针
        ptr = d / "factory_report.json"
        ptr.write_text(
            json.dumps(
                {
                    "run_id": genome.get("source", {}).get("run_id"),
                    "rolefactory_report": f"YiAgent/rolefactory/data/runs/{genome.get('source', {}).get('run_id')}/report.json",
                    "synced_at": _now(),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append(p)
        print(f"  wrote {p}", flush=True)
    return written


def _genome_hash(genome: dict) -> str:
    """与 tools/genome_card.py 同一套规范哈希：只由 role_id + 每槽 allele_id + 文本 sha256 决定。"""
    try:
        from genome_card import SLOTS, _sha256  # 同目录

        slots = genome.get("slots") or {}
        canon = {
            "role_id": (genome.get("source") or {}).get("role_id") or "",
            "slots": {
                s: {
                    "allele_id": (slots.get(s) or {}).get("allele_id"),
                    "text_sha256": _sha256(str((slots.get(s) or {}).get("text") or "")),
                }
                for s in SLOTS
            },
        }
        return _sha256(json.dumps(canon, ensure_ascii=False, sort_keys=True))
    except Exception:  # noqa: BLE001 登记表不因哈希失败而写不出来
        return ""


def write_registry(rows: list[dict]) -> None:
    REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Develop 开发编队 · factory 真实构建登记",
        "",
        f"- 更新：{_now()}",
        "- 工厂：`rolefactory` `http://127.0.0.1:8790`",
        "- 运行时基因组：`YiAgent/console/_workbench/AgentTeam/Develop/{Role}/genome.json`",
        "- 工作台副本：`A002.YiAgent/工作台/AgentTeam/Develop/{Role}/genome.json`",
        "- 基因组卡（含内容哈希 / 逐槽消融 / 复现配方）：`YiAgent/rolefactory/data/runs/{run_id}/genome_card.md`",
        "",
        "| 席位 | factory 角色名 | run_id | 冠军加权 | Δ基线(train) | holdout Δ | genome_hash | 路径 |",
        "|------|----------------|--------|----------|--------------|-----------|-------------|------|",
    ]
    for r in rows:
        src = r.get("source") or {}
        hold = src.get("holdout") or {}
        h = _genome_hash(r)
        lines.append(
            f"| {r.get('role')} | {r.get('factory_role')} | `{src.get('run_id')}` | "
            f"{src.get('champion_weighted')} | {src.get('delta_train_weighted')} | "
            f"{hold.get('delta_weighted')} | `{h[:16] or '—'}` | "
            f"`AgentTeam/Develop/{r.get('role')}/genome.json` |"
        )
    lines += [
        "",
        "## 说明",
        "",
        "- 分数来自 rolefactory 客观断言实跑，非冻结演示。",
        "- bridge `developRoles` 读取 runtime `_workbench/AgentTeam/Develop/*/genome.json`。",
        "- `genome_hash` 取前 16 位展示；校验落盘基因组是否就是该次实跑的冠军：",
        "  `python tools/genome_card.py verify <run_id> <genome.json>`。",
        "",
    ]
    REG_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote registry {REG_PATH}", flush=True)


def load_existing_genomes() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for meta in TEAM:
        p = RUNTIME_WB / meta["seat"] / "genome.json"
        if p.exists():
            try:
                g = json.loads(p.read_text(encoding="utf-8"))
                if g.get("source", {}).get("run_id"):
                    out[meta["seat"]] = g
            except Exception:
                pass
    return out


def build_one(meta: dict, *, attempts: int = 3) -> dict:
    seat = meta["seat"]
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        print(f"\n=== BUILD {seat} / {meta['factory_role']} (attempt {attempt}/{attempts}) ===", flush=True)
        try:
            rid = start_run(meta["factory_role"])
            report = wait_run(rid)
            arch = DOC_WB.parent / "factory-runs" / f"{seat}-{rid}.json"
            arch.parent.mkdir(parents=True, exist_ok=True)
            src = HERE / "data" / "runs" / rid / "report.json"
            if src.exists():
                shutil.copy(src, arch)
            genome = report_to_genome(seat, meta, report)
            write_genome(seat, genome)
            print(
                f"  DONE {seat} pass@champ={genome['source'].get('champion_weighted')} "
                f"delta={genome['source'].get('delta_train_weighted')}",
                flush=True,
            )
            return genome
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  FAIL {seat} attempt {attempt}: {e}", flush=True)
            time.sleep(5)
    raise RuntimeError(f"{seat} failed after {attempts} attempts: {last_err}")


def main() -> int:
    import sys

    only = {a for a in sys.argv[1:] if not a.startswith("-")}
    hz = _http("GET", "/healthz")
    if not hz.get("ok") or not hz.get("key_present"):
        raise SystemExit(f"rolefactory not ready: {hz}")
    print("rolefactory ok", hz.get("model"), flush=True)

    existing = load_existing_genomes()
    genomes: list[dict] = []
    failures: list[str] = []
    for meta in TEAM:
        seat = meta["seat"]
        if only and seat not in only and meta["factory_role"] not in only:
            if seat in existing:
                genomes.append(existing[seat])
            continue
        if seat in existing and not only:
            print(f"skip existing {seat} run={existing[seat].get('source', {}).get('run_id')}", flush=True)
            genomes.append(existing[seat])
            continue
        try:
            genomes.append(build_one(meta, attempts=3))
        except Exception as e:  # noqa: BLE001
            failures.append(f"{seat}:{e}")
            print(f"GIVE UP {seat}: {e}", flush=True)

    write_registry(genomes)
    if failures:
        print("FAILURES", failures, flush=True)
    # 总清单
    summary = {
        "built_at": _now(),
        "seats": [
            {
                "seat": g["role"],
                "run_id": g["source"]["run_id"],
                "champion_weighted": g["source"].get("champion_weighted"),
                "delta_train_weighted": g["source"].get("delta_train_weighted"),
            }
            for g in genomes
        ],
    }
    (DOC_WB.parent / "devteam-build-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nALL DONE", json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
