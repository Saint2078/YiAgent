"""批量鉴定 + 多代进化引擎：manifest 测试集 × 基因组 bank。

每代：variants × manifest.cases × eval_reps 批量鉴定 → 评分卡落盘 →
精英保留 + 交叉 + LLM 邻域精炼产下一代 → 门禁裁决（停滞 / 代数 / token 预算）。
结束后总冠军在 holdout 集终验，可选 arm A 基线对照，产出 report.json/report.md。
复用 jobs.py 的 calc_stats / pick_marks 与 assemble/judge/llm_client 既有件。
"""

from __future__ import annotations

import json
import logging
import math
import random
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from assemble import (
    assemble_system,
    build_baseline_messages,
    build_messages,
    host_of,
    judge_body,
)
from eval_cache import cache_get, cache_put, gene_hash_of
from generate import generate_case, generate_genomes, refine_genomes
from jobs import calc_stats, pick_marks
from judge import judge_with_retries
from llm_client import chat_completions, extract_content
from run_log import get_or_create_log
from testset import build_manifest, load_manifest, resolve_cases, save_manifest
from token_meter import TokenMeter
from yiagent.providers.usage import derive_usage


def wall_by_stage(marks: list[dict], t0: float) -> list[dict[str, Any]]:
    """分阶段墙钟：相邻 mark 时间戳差值（首段从 t0=run 创建时刻起算）。

    与 token_by_stage 同结构并列：[{stage, seconds, pct}]，pct 为占总墙钟百分比
    （总墙钟 = 末次 mark − t0；为 0 时 pct 记 None）。纯函数，可注入假时间单测。
    """
    rows: list[dict[str, Any]] = []
    prev = float(t0)
    for m in marks or []:
        ts = float(m.get("ts") or prev)
        rows.append({"stage": m.get("stage"), "seconds": round(max(0.0, ts - prev), 2)})
        prev = ts
    total = round(sum(r["seconds"] for r in rows), 2)
    for r in rows:
        r["pct"] = round(r["seconds"] / total * 100, 1) if total > 0 else None
    return rows


def _usage_delta(prev: dict, cur: dict) -> dict[str, Any]:
    """两个 meter.summary() 快照的差值（含计费派生字段）。"""
    raw = {
        k: int(cur.get(k) or 0) - int(prev.get(k) or 0)
        for k in ("prompt_tokens", "completion_tokens", "cached_tokens", "total_tokens")
    }
    return {
        "calls": int(cur.get("calls") or 0) - int(prev.get("calls") or 0),
        **derive_usage(raw),
    }

ROOT = Path(__file__).resolve().parents[1]
EVOLVE_DIR = ROOT / "save" / "evolve"

SLOTS = ["G1", "G2", "G3", "G4", "G5"]

# 低分维度 → 槽建议（归因约定：指令遵循类→G4/G5，知识类→G3，其余默认 G4）
_DIM_KNOWLEDGE = ("知识", "knowledge", "事实", "factual", "准确", "accuracy", "专业")
_DIM_INSTRUCT = ("指令", "instruction", "遵循", "任务", "完成", "格式", "format", "边界", "合规")


def composite(stats: dict) -> float | None:
    """均衡分 = mean − 1.5·sdv（与 pick_marks 的 balanced 同口径）。"""
    mean = stats.get("mean")
    if mean is None:
        return None
    return round(float(mean) - 1.5 * float(stats.get("sdv") or 0), 2)


def crossover(
    bank: dict,
    parent_a: dict,
    parent_b: dict,
    *,
    new_id: str,
    rng: random.Random,
) -> dict:
    """纯函数交叉：G1 固定取 parent_a；G2–G5 每槽随机取两亲本之一的等位 id。"""
    alleles = bank.get("alleles") or {}
    slots_a = parent_a.get("slots") or {}
    slots_b = parent_b.get("slots") or {}
    slots: dict[str, str] = {}
    for s in SLOTS:
        legal = [a.get("id") for a in alleles.get(s) or [] if a.get("id")]
        if s == "G1":
            aid = slots_a.get(s)
        else:
            aid = rng.choice([slots_a.get(s), slots_b.get(s)])
        if aid not in legal:
            aid = legal[0] if legal else None
        slots[s] = str(aid or "")
    return {
        "id": new_id,
        "hash": f"yg-x-{uuid.uuid4().hex[:8]}",
        "title": f"交叉 {parent_a.get('id')}×{parent_b.get('id')}",
        "slots": slots,
        "role_in_demo": "crossover",
    }


def random_immigrant(bank: dict, *, new_id: str, rng: random.Random) -> dict:
    """随机移民：无种子随机重组——每槽从等位库均匀随机取一个等位，防早熟。

    与 crossover 不同，不偏向任何亲本（G1 也随机）；role_in_demo="immigrant"
    使种群中可标识来源。
    """
    alleles = bank.get("alleles") or {}
    slots: dict[str, str] = {}
    for s in SLOTS:
        legal = [a.get("id") for a in alleles.get(s) or [] if a.get("id")]
        slots[s] = str(rng.choice(legal)) if legal else ""
    return {
        "id": new_id,
        "hash": f"yg-i-{uuid.uuid4().hex[:8]}",
        "title": f"随机移民 {new_id}",
        "slots": slots,
        "role_in_demo": "immigrant",
    }


def select_elites(scorecards: list[dict], k: int) -> list[dict]:
    """按 composite 取前 k 个评分卡（精英保留）；unreliable（失败率>50%）不参与评选。"""
    scored = [
        c
        for c in scorecards
        if c.get("composite") is not None and not c.get("unreliable")
    ]
    scored.sort(key=lambda c: (-float(c["composite"]), -float(c.get("mean") or 0)))
    return scored[: max(0, int(k))]


def gate_verdict(
    history: list[float], improve_threshold: float, stagnation_limit: int
) -> dict[str, Any]:
    """相邻两代冠军 composite 提升判定：promote|stagnant|stop。

    提升 < improve_threshold 记一次停滞；连续停滞累计 >= stagnation_limit 判 stop。
    """
    if len(history) < 2:
        return {
            "verdict": "promote",
            "reason": "first_generation",
            "stagnant_count": 0,
            "improvement": None,
        }
    improvement = round(float(history[-1]) - float(history[-2]), 2)
    stagnant = 0
    for i in range(len(history) - 1, 0, -1):
        if float(history[i]) - float(history[i - 1]) < improve_threshold:
            stagnant += 1
        else:
            break
    if stagnant >= int(stagnation_limit):
        return {
            "verdict": "stop",
            "reason": f"stagnant {stagnant} >= limit {stagnation_limit}",
            "stagnant_count": stagnant,
            "improvement": improvement,
        }
    if improvement < improve_threshold:
        return {
            "verdict": "stagnant",
            "reason": f"improvement {improvement} < threshold {improve_threshold}",
            "stagnant_count": stagnant,
            "improvement": improvement,
        }
    return {
        "verdict": "promote",
        "reason": f"improvement {improvement} >= threshold {improve_threshold}",
        "stagnant_count": 0,
        "improvement": improvement,
    }


def _betacf(a: float, b: float, x: float) -> float:
    """连分式求不完全 beta（Numerical Recipes betacf），供 t 分布 p 值用。"""
    max_iter, eps, fpmin = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """正则化不完全 beta 函数 I_x(a, b)（纯 python）。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _paired_t_pvalue(diffs: list[float], diff_mean: float, sd: float) -> float:
    """配对学生 t 检验双侧 p 值（df = n-1）；零方差退化：差值为 0 → p=1，否则 p=0。"""
    n = len(diffs)
    if sd == 0:
        return 1.0 if diff_mean == 0 else 0.0
    t = abs(diff_mean) / (sd / math.sqrt(n))
    df = n - 1
    return round(_betai(df / 2, 0.5, df / (df + t * t)), 6)


def paired_gate(
    champ_by_case: dict[str, list[float]],
    prev_by_case: dict[str, list[float]],
    *,
    alpha: float = 0.05,
    n_boot: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """按题配对的显著性门禁：两变体在共有题上的逐题均分差 → 配对 t 检验 + bootstrap CI。

    判定语义：bootstrap 均值差 CI 下界 > 0 → promote（显著提升）；CI 上界 < 0 →
    regress（显著退步）；CI 跨 0 → stagnant。共有题 < 2 时退化（method=
    insufficient_data，verdict 保守取 stagnant，调用方应退回固定阈值逻辑）。
    bootstrap 用 random.Random(seed) 确定性重抽样，同输入同 seed 结果可复现。
    """
    diffs: list[float] = []
    for key in sorted(set(champ_by_case) & set(prev_by_case)):
        a = [float(s) for s in champ_by_case.get(key) or []]
        b = [float(s) for s in prev_by_case.get(key) or []]
        if a and b:
            diffs.append(statistics.mean(a) - statistics.mean(b))
    n = len(diffs)
    if n < 2:
        return {
            "verdict": "stagnant",
            "diff_mean": round(statistics.mean(diffs), 2) if diffs else None,
            "ci_low": None,
            "ci_high": None,
            "p_value": None,
            "n_cases": n,
            "method": "insufficient_data",
        }
    diff_mean = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    p_value = _paired_t_pvalue(diffs, diff_mean, sd)
    rng = random.Random(seed)
    boot = sorted(
        statistics.mean(rng.choice(diffs) for _ in range(n)) for _ in range(int(n_boot))
    )
    lo_i = max(0, min(int(n_boot) - 1, int((alpha / 2) * n_boot)))
    hi_i = max(0, min(int(n_boot) - 1, int((1 - alpha / 2) * n_boot)))
    ci_low, ci_high = round(boot[lo_i], 2), round(boot[hi_i], 2)
    if ci_low > 0:
        verdict = "promote"
    elif ci_high < 0:
        verdict = "regress"
    else:
        verdict = "stagnant"
    return {
        "verdict": verdict,
        "diff_mean": round(diff_mean, 2),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": p_value,
        "n_cases": n,
        "method": "paired_t+bootstrap",
    }


def _scores_by_case(card: dict) -> dict[str, list[float]]:
    """评分卡逐题明细 → {suite/id: [各 rep 分数]}（空分数的题不纳入配对）。"""
    out: dict[str, list[float]] = {}
    for case in card.get("cases") or []:
        scores = [float(s) for s in case.get("scores") or []]
        if scores:
            out[f"{case.get('suite')}/{case.get('id')}"] = scores
    return out


def summarize_failures(failure_stats: dict[str, dict[str, int]]) -> dict[str, Any]:
    """逐变体与全局评分失败率汇总（failed_runs/total_runs）；聚合失败率 > 50% 标 unreliable。"""
    by_variant: dict[str, dict[str, Any]] = {}
    total_failed = 0
    total_runs = 0
    for vid in sorted(failure_stats):
        st = failure_stats[vid] or {}
        failed = int(st.get("failed_runs") or 0)
        runs = int(st.get("total_runs") or 0)
        total_failed += failed
        total_runs += runs
        rate = round(failed / runs, 4) if runs else None
        by_variant[vid] = {
            "failed_runs": failed,
            "total_runs": runs,
            "rate": rate,
            "unreliable": bool(rate is not None and rate > 0.5),
        }
    return {
        "global": {
            "failed_runs": total_failed,
            "total_runs": total_runs,
            "rate": round(total_failed / total_runs, 4) if total_runs else None,
        },
        "by_variant": by_variant,
    }


def stratify_scores(per_case: list[dict]) -> dict[str, Any]:
    """评分卡逐题明细按题型/套件分层均分（治 composite 被题间方差绑架的呈现层）。

    分层依据优先级：test_type 题型字段 → suite 套件字段；都没有 → method="none"
    并在 note 注明无法分层的原因。每层对该层全部 rep 分数做 calc_stats。
    """
    rows = [c for c in per_case or [] if isinstance(c, dict)]
    if any(r.get("test_type") for r in rows):
        key_field = "test_type"
    elif any(r.get("suite") for r in rows):
        key_field = "suite"
    else:
        return {
            "method": "none",
            "layers": {},
            "note": "题目元数据无 test_type/suite 字段，无法按题型/套件分层",
        }
    groups: dict[str, list[float]] = {}
    for r in rows:
        key = str(r.get(key_field) or "未标注")
        groups.setdefault(key, []).extend(
            float(s) for s in r.get("scores") or [] if s is not None
        )
    layers = {key: calc_stats(scores) for key, scores in sorted(groups.items())}
    return {"method": key_field, "layers": layers, "note": ""}


def _slots_for_dimension(dim: str) -> list[str]:
    """单个低分维度 → 槽建议。"""
    name = (dim or "").lower()
    if any(k in name for k in _DIM_KNOWLEDGE):
        return ["G3"]
    if any(k in name for k in _DIM_INSTRUCT):
        return ["G4", "G5"]
    return ["G4"]


def attribute_failure(scorecards: list[dict]) -> dict[str, Any]:
    """冠军低分维度归因：汇总每维均分，取最低 2–3 维，给槽建议与 failure_notes。"""
    acc: dict[str, list[float]] = {}
    for card in scorecards or []:
        dims = card.get("dimension_scores")
        if isinstance(dims, dict):
            items = dims.items()
        else:
            items = []
            for case in card.get("cases") or []:
                for dim, val in (case.get("dimension_scores") or {}).items():
                    acc.setdefault(dim, []).append(float(val))
        for dim, val in items:
            acc.setdefault(dim, []).append(float(val))
    means = [
        {"dimension": dim, "mean": round(sum(vals) / len(vals), 2)}
        for dim, vals in acc.items()
        if vals
    ]
    means.sort(key=lambda x: x["mean"])
    low = means[:3] if len(means) >= 3 else means[:2]
    slot_hints = {row["dimension"]: _slots_for_dimension(row["dimension"]) for row in low}
    lines = [
        f"- {row['dimension']}：均分 {row['mean']}，建议改 {'/'.join(slot_hints[row['dimension']])}"
        for row in low
    ]
    notes = "冠军基因组低分维度归因（按均分升序取最低 2–3 维）：\n" + "\n".join(lines) if lines else ""
    return {"low_dims": low, "slot_hints": slot_hints, "failure_notes": notes}


def _seed_from_variant(bank: dict, variant_id: str) -> dict:
    """从 bank + variant 重建 refine 种子（slots + slot_texts，同 jobs.py 约定）。"""
    variant = None
    for v in bank.get("variants") or []:
        if v.get("id") == variant_id:
            variant = v
            break
    if not variant:
        raise ValueError(f"variant missing in bank: {variant_id}")
    slots = dict(variant.get("slots") or {})
    alleles = bank.get("alleles") or {}
    slot_texts: dict[str, Any] = {}
    for slot, allele_id in slots.items():
        allele = None
        for a in alleles.get(slot) or []:
            if a.get("id") == allele_id:
                allele = {"id": a.get("id"), "label": a.get("label"), "text": a.get("text")}
                break
        slot_texts[slot] = {"allele_id": allele_id, "allele": allele}
    return {
        "variant_id": variant.get("id"),
        "title": variant.get("title"),
        "hash": variant.get("hash"),
        "slots": slots,
        "slot_texts": slot_texts,
        "skills": variant.get("skills") or [],
    }


def _trim_variants(bank: dict, n: int) -> dict:
    """裁剪 bank 的 variants 到 n 个（保持顺序）。"""
    variants = list(bank.get("variants") or [])
    return {**bank, "variants": variants[: max(1, int(n))]}


def _merge_banks(
    cur_bank: dict, refined_bank: dict, variants: list[dict], n: int
) -> dict:
    """合并等位库 + variants（精英 + 交叉 + 精炼邻域），按 id 去重，裁到 n。"""
    merged_alleles: dict[str, list] = {}
    for slot in SLOTS:
        by_id: dict[str, dict] = {}
        for source in (refined_bank, cur_bank):
            for a in (source.get("alleles") or {}).get(slot) or []:
                if isinstance(a, dict) and a.get("id"):
                    by_id.setdefault(str(a["id"]), dict(a))
        merged_alleles[slot] = list(by_id.values())
    seen: set[str] = set()
    uniq: list[dict] = []
    for v in variants:
        vid = str(v.get("id") or "")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        uniq.append(v)
    return {
        "meta": dict(cur_bank.get("meta") or {}),
        "alleles": merged_alleles,
        "variants": uniq[: max(1, int(n))],
    }


def _variant_of(bank: dict, variant_id: str) -> dict | None:
    for v in bank.get("variants") or []:
        if v.get("id") == variant_id:
            return v
    return None


def _eval_one_variant(
    *,
    api_key: str,
    model: str,
    case: dict,
    bank: dict,
    variant: dict,
    rep: int,
    abort: threading.Event,
    meter: TokenMeter | None = None,
) -> dict[str, Any]:
    """单 variant × 单题 × 单 rep：host 原题 + 基因组 system，裁判按本题 criteria。"""
    ctx = meter.activate() if meter is not None else nullcontext()
    with ctx:
        vid = str(variant.get("id"))
        if abort.is_set():
            return {"aborted": True, "variant_id": vid, "rep": rep}
        host = host_of(case.get("messages") or [])
        system = assemble_system(host, bank, variant)
        messages = build_messages(case, system)
        gen = chat_completions(
            api_key, model, messages, max_tokens=2200, reasoning_effort="low", purpose="answer"
        )
        content = extract_content(gen)
        if abort.is_set():
            return {"aborted": True, "variant_id": vid, "rep": rep}
        jr = judge_with_retries(api_key, model, judge_body(case), content, max_attempts=3)
        return {
            "variant_id": vid,
            "rep": rep,
            "score": float(jr["score"]) if jr.get("score") is not None else None,
            "ok": jr.get("ok"),
            "dimension_scores": dict(jr.get("scores_used") or {}),
            "preview": (content or "")[:280],
        }


def _eval_one_baseline(
    *,
    api_key: str,
    model: str,
    case: dict,
    rep: int,
    abort: threading.Event,
    meter: TokenMeter | None = None,
) -> dict[str, Any]:
    """arm A 基线：host 原题，不加任何基因组。"""
    ctx = meter.activate() if meter is not None else nullcontext()
    with ctx:
        if abort.is_set():
            return {"aborted": True, "arm": "A", "rep": rep}
        messages = build_baseline_messages(case, "A")
        gen = chat_completions(
            api_key, model, messages, max_tokens=2200, reasoning_effort="low", purpose="answer"
        )
        content = extract_content(gen)
        if abort.is_set():
            return {"aborted": True, "arm": "A", "rep": rep}
        jr = judge_with_retries(api_key, model, judge_body(case), content, max_attempts=3)
        return {
            "arm": "A",
            "rep": rep,
            "score": float(jr["score"]) if jr.get("score") is not None else None,
            "ok": jr.get("ok"),
            "dimension_scores": dict(jr.get("scores_used") or {}),
            "preview": (content or "")[:280],
        }


def _agg_dimension_scores(rows: list[dict]) -> dict[str, float]:
    """多 rep 的 dimension_scores 汇总为每维均分。"""
    acc: dict[str, list[float]] = {}
    for row in rows:
        for dim, val in (row.get("dimension_scores") or {}).items():
            try:
                acc.setdefault(dim, []).append(float(val))
            except (TypeError, ValueError):
                continue
    return {dim: round(sum(vals) / len(vals), 2) for dim, vals in acc.items() if vals}


@dataclass
class EvolveRun:
    id: str
    model: str = "k3"
    demand: str = ""
    manifest_id: str | None = None
    status: str = "pending"  # pending|running|done|error|aborted
    phase: str = "init"  # init|eval|refine|final|report|done
    generation: int = -1
    total: int = 0
    done: int = 0
    params: dict[str, Any] = field(default_factory=dict)
    champion_curve: list[dict] = field(default_factory=list)
    gates: list[dict] = field(default_factory=list)
    failure_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    stop_reason: str | None = None
    champion: dict[str, Any] | None = None
    holdout_summary: dict[str, Any] | None = None
    baseline_summary: dict[str, Any] | None = None
    error: str | None = None
    report_json: str | None = None
    report_md: str | None = None
    token_meter: TokenMeter = field(default_factory=TokenMeter)
    token_marks: list[dict] = field(default_factory=list)  # [{stage, usage}] 分阶段快照
    cache_hits: int = 0  # 本地评估缓存命中次数（跳过的 LLM 调用）
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    _abort: threading.Event = field(default_factory=threading.Event)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "id": self.id,
                "status": self.status,
                "phase": self.phase,
                "model": self.model,
                "demand": self.demand,
                "manifest_id": self.manifest_id,
                "generation": self.generation,
                "total": self.total,
                "done": self.done,
                "params": dict(self.params),
                "champion_curve": list(self.champion_curve),
                "gates": list(self.gates),
                "failure_stats": {k: dict(v) for k, v in self.failure_stats.items()},
                "stop_reason": self.stop_reason,
                "champion": dict(self.champion) if self.champion else None,
                "holdout_summary": dict(self.holdout_summary) if self.holdout_summary else None,
                "baseline_summary": dict(self.baseline_summary) if self.baseline_summary else None,
                "error": self.error,
                "report_json": self.report_json,
                "report_md": self.report_md,
                "token_usage": self.token_meter.summary(),
                "token_marks": [
                    {"stage": m.get("stage"), "usage": m.get("usage"), "ts": m.get("ts")}
                    for m in self.token_marks
                ],
                "cache_hits": self.cache_hits,
                "updated_at": self.updated_at,
            }


class EvolveManager:
    def __init__(self) -> None:
        self._runs: dict[str, EvolveRun] = {}
        self._lock = threading.Lock()

    def get(self, run_id: str) -> EvolveRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def _require(self, run_id: str) -> EvolveRun:
        run = self.get(run_id)
        if not run:
            raise KeyError(run_id)
        return run

    def start(
        self,
        api_key: str,
        model: str,
        *,
        manifest_id: str | None = None,
        manifest: dict | None = None,
        oral: str | None = None,
        seed: dict | None = None,
        max_generations: int = 4,
        variants_per_gen: int = 6,
        eval_reps: int = 2,
        final_reps: int = 3,
        workers: int = 4,
        pass_mean: float = 70.0,
        elite_k: int = 2,
        stagnation_limit: int = 2,
        improve_threshold: float = 1.0,
        max_tokens_budget: int | None = None,
        anchor_case: dict | None = None,
        with_baseline: bool = True,
        use_cache: bool = True,
    ) -> EvolveRun:
        """启动后台 evolution run。manifest / manifest_id / oral 至少给一个。"""
        if not manifest_id and not manifest and not (oral or "").strip():
            raise ValueError("manifest_id / manifest / oral 至少给一个")
        if manifest is None:
            if manifest_id:
                manifest = load_manifest(manifest_id)
            else:
                manifest = build_manifest(demand=(oral or "").strip())
                save_manifest(manifest)
        if not (manifest.get("cases") or []):
            raise ValueError("manifest.cases empty")
        run = EvolveRun(
            id=uuid.uuid4().hex[:12],
            model=model,
            demand=str(manifest.get("demand") or oral or ""),
            manifest_id=str(manifest.get("id") or manifest_id or ""),
            params={
                "max_generations": max(1, min(int(max_generations), 10)),
                "variants_per_gen": max(2, min(int(variants_per_gen), 12)),
                "eval_reps": max(1, min(int(eval_reps), 10)),
                "final_reps": max(1, min(int(final_reps), 10)),
                "workers": max(1, min(int(workers), 12)),
                "pass_mean": float(pass_mean),
                "elite_k": max(1, min(int(elite_k), 6)),
                "stagnation_limit": max(1, min(int(stagnation_limit), 5)),
                "improve_threshold": float(improve_threshold),
                "max_tokens_budget": int(max_tokens_budget) if max_tokens_budget else None,
                "with_baseline": bool(with_baseline),
                "use_cache": bool(use_cache),
                "seeded": bool(seed),
                "manifest_cases": len(manifest.get("cases") or []),
                "manifest_holdout": len(manifest.get("holdout") or []),
            },
        )
        with self._lock:
            self._runs[run.id] = run
        rlog = get_or_create_log(run.id, model=model, oral=run.demand)
        rlog.record_phase("init", note=f"evolve manifest={run.manifest_id}")
        threading.Thread(
            target=self._run,
            args=(run, api_key, manifest, seed, anchor_case),
            daemon=True,
        ).start()
        return run

    def abort(self, run_id: str) -> EvolveRun:
        run = self._require(run_id)
        run._abort.set()
        with run.lock:
            if run.status in ("pending", "running"):
                run.status = "aborted"
            run.updated_at = time.time()
        return run

    # ---- 内部 ----

    def _set(self, run: EvolveRun, **kw: Any) -> None:
        with run.lock:
            for k, v in kw.items():
                setattr(run, k, v)
            run.updated_at = time.time()

    def _run(
        self,
        run: EvolveRun,
        api_key: str,
        manifest: dict,
        seed: dict | None,
        anchor_case: dict | None,
    ) -> None:
        try:
            self._run_inner(run, api_key, manifest, seed, anchor_case)
        except Exception as e:  # noqa: BLE001
            self._set(run, status="error", phase="error", error=str(e))
            rlog = get_or_create_log(run.id, model=run.model, oral=run.demand)
            rlog.record_phase("error", note=str(e))

    def _run_inner(
        self,
        run: EvolveRun,
        api_key: str,
        manifest: dict,
        seed: dict | None,
        anchor_case: dict | None,
    ) -> None:
        p = run.params
        run_dir = EVOLVE_DIR / run.id
        run_dir.mkdir(parents=True, exist_ok=True)
        self._set(run, status="running", phase="init")
        cases = resolve_cases(manifest, "cases")
        holdout_cases = resolve_cases(manifest, "holdout") if manifest.get("holdout") else []

        # 第 0 代 bank：seed 精炼 或 锚点题 + generate_genomes
        meter = run.token_meter
        with meter.activate():
            if seed:
                anchor = anchor_case or cases[0]
                bank = refine_genomes(api_key, run.model, anchor, seed)
            else:
                anchor = anchor_case or generate_case(
                    api_key, run.model, run.demand or "鉴定基因组"
                )
                bank = generate_genomes(api_key, run.model, anchor)
        bank = _trim_variants(bank, p["variants_per_gen"])
        self._mark(run, "init")
        rlog = get_or_create_log(run.id, model=run.model, oral=run.demand)
        rlog.record_genomes(bank=bank)

        history: list[float] = []
        best: dict[str, Any] | None = None  # {composite, gen, variant, bank, scorecard}
        stop_reason = "max_generations"
        stagnant_streak = 0
        prev_champ_cases: dict[str, list[float]] | None = None
        evolution_ops: list[dict] = []  # 每代进化算子记录（变异档位 + 随机移民）

        for gen in range(int(p["max_generations"])):
            if run._abort.is_set():
                stop_reason = "aborted"
                break
            self._set(run, generation=gen, phase="eval")
            scorecards = self._evaluate_generation(
                run, api_key, bank, cases, gen, run_dir
            )
            self._mark(run, f"gen{gen}_eval")
            if run._abort.is_set():
                stop_reason = "aborted"
                break
            ranked = select_elites(scorecards, len(scorecards))
            if not ranked:
                raise RuntimeError(f"gen{gen}: no scored variants")
            champion_card = ranked[0]
            champ_comp = float(champion_card["composite"])
            history.append(champ_comp)
            with run.lock:
                run.champion_curve.append(
                    {
                        "gen": gen,
                        "variant_id": champion_card["variant_id"],
                        "mean": champion_card.get("mean"),
                        "sdv": champion_card.get("sdv"),
                        "composite": champ_comp,
                    }
                )
                run.updated_at = time.time()
            if best is None or champ_comp > float(best["composite"]):
                best = {
                    "composite": champ_comp,
                    "gen": gen,
                    "variant_id": champion_card["variant_id"],
                    "variant": _variant_of(bank, champion_card["variant_id"]),
                    "bank": bank,
                    "scorecard": champion_card,
                }

            # 门禁与终止：优先按题配对显著性判定（当代冠军 vs 上代冠军）；
            # 配对题不足（n_cases<2，含首代）时退回固定阈值逻辑。
            # 语义：promote 重置停滞计数；stagnant/regress 均累计一次停滞，
            # 连续达 stagnation_limit 判 stop（regress 视为比停滞更强的停止信号，同口径计数）。
            champ_by_case = _scores_by_case(champion_card)
            paired = paired_gate(champ_by_case, prev_champ_cases) if prev_champ_cases else None
            if paired is not None and paired["n_cases"] >= 2:
                verdict = str(paired["verdict"])
                stagnant_streak = 0 if verdict == "promote" else stagnant_streak + 1
                if stagnant_streak >= int(p["stagnation_limit"]):
                    gate = {
                        "verdict": "stop",
                        "reason": (
                            f"paired {verdict} streak {stagnant_streak}"
                            f" >= limit {p['stagnation_limit']}"
                        ),
                    }
                else:
                    gate = {
                        "verdict": verdict,
                        "reason": (
                            f"paired {verdict}: diff {paired['diff_mean']}"
                            f" CI[{paired['ci_low']}, {paired['ci_high']}] p={paired['p_value']}"
                        ),
                    }
                gate["stagnant_count"] = stagnant_streak
                gate["improvement"] = paired["diff_mean"]
                gate["method"] = paired["method"]
                gate["paired"] = paired
            else:
                gate = gate_verdict(history, p["improve_threshold"], p["stagnation_limit"])
                gate["method"] = "fixed_threshold"
                gate["paired"] = paired
                stagnant_streak = int(gate["stagnant_count"])
            prev_champ_cases = champ_by_case
            budget = p.get("max_tokens_budget")
            if budget and meter.total_tokens > int(budget):
                gate = {
                    **gate,
                    "verdict": "stop",
                    "reason": f"token budget exceeded: {meter.total_tokens} > {budget}",
                }
            gate_row = {"gen": gen, **gate}
            with run.lock:
                run.gates.append(gate_row)
                run.updated_at = time.time()
            self._write_gen_summary(run_dir, gen, scorecards, ranked, gate_row)
            if gate["verdict"] == "stop":
                stop_reason = gate["reason"]
                break
            if gen >= int(p["max_generations"]) - 1:
                stop_reason = "max_generations"
                break

            # 进化算子产下一代：停滞计数 > 0 升级为大开角重写（wide），提升后回落 local
            self._set(run, phase="refine")
            mutation_level = "wide" if stagnant_streak > 0 else "local"
            bank = self._next_generation(
                run,
                api_key,
                bank,
                anchor,
                scorecards,
                ranked,
                gen,
                mutation_level=mutation_level,
            )
            ops = dict((bank.get("meta") or {}).get("evolve_ops") or {})
            if ops:
                evolution_ops.append(ops)
            self._mark(run, f"gen{gen}_refine")
            rlog.record_genomes(bank=bank)

        if best is None:
            if run._abort.is_set():
                self._set(run, status="aborted", stop_reason="aborted")
                return
            raise RuntimeError("no generation evaluated")

        self._set(
            run,
            phase="final",
            stop_reason=stop_reason,
            champion={
                "gen": best["gen"],
                "variant_id": best["variant_id"],
                "composite": best["composite"],
                "slots": (best["variant"] or {}).get("slots") or {},
            },
        )

        # 终验：总冠军 × holdout × final_reps
        holdout_summary = None
        if holdout_cases and not run._abort.is_set():
            holdout_summary = self._final_holdout(
                run, api_key, best, holdout_cases, run_dir
            )
            self._mark(run, "final_holdout")
        # 对照：arm A 基线 × manifest.cases × eval_reps
        baseline_summary = None
        if p.get("with_baseline") and not run._abort.is_set():
            baseline_summary = self._final_baseline(run, api_key, cases, run_dir)
            self._mark(run, "baseline_a")

        self._set(run, holdout_summary=holdout_summary, baseline_summary=baseline_summary)
        if run._abort.is_set():
            self._set(run, status="aborted", stop_reason="aborted")
            return

        # 报告
        self._set(run, phase="report")
        report = self._build_report(
            run, manifest, best, holdout_summary, baseline_summary, evolution_ops
        )
        report_json = run_dir / "report.json"
        report_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        report_md = run_dir / "report.md"
        report_md.write_text(self._render_report_md(report), encoding="utf-8")
        self._set(
            run,
            status="done",
            phase="done",
            report_json=str(report_json.relative_to(ROOT)),
            report_md=str(report_md.relative_to(ROOT)),
        )
        rlog.token_usage = run.token_meter.summary()
        rlog.record_phase("done", note=f"evolve stop={stop_reason}")
        rlog.write_local(label="evolve", version_tag="v0.1")
        # 名人堂上报钩子（严格 opt-in）：异常只记日志，不影响 run 状态
        try:
            from hof_ship import auto_ship_run

            auto_ship_run(run_dir)
        except Exception:  # noqa: BLE001
            logging.getLogger("factory.evolve").exception(
                "hof auto ship hook failed (run unaffected)"
            )

    def _mark(self, run: EvolveRun, stage: str) -> None:
        """记录一个阶段的 token + 墙钟快照（report 里做差值得分阶段账单/耗时）。"""
        with run.lock:
            run.token_marks.append(
                {"stage": stage, "usage": run.token_meter.summary(), "ts": time.time()}
            )
            run.updated_at = time.time()

    def _evaluate_generation(
        self,
        run: EvolveRun,
        api_key: str,
        bank: dict,
        cases: list[dict],
        gen: int,
        run_dir: Path,
    ) -> list[dict]:
        """一代批量鉴定：variants × cases × eval_reps → 评分卡落盘。"""
        p = run.params
        reps = int(p["eval_reps"])
        use_cache = bool(p.get("use_cache", True))
        variants = [v for v in bank.get("variants") or [] if v.get("id")]
        rows: dict[str, dict[str, list[dict]]] = {}  # vid → case_key → rows
        tasks: list[tuple[dict, dict, int]] = []
        cached_done = 0
        for v in variants:
            vid = str(v["id"])
            gh = gene_hash_of(v) if use_cache else ""
            for c in cases:
                case_key = f"{c.get('suite')}/{c.get('id')}"
                hit: list[float] = []
                if use_cache:
                    ent = cache_get(gh, run.model, c)
                    hit = [float(s) for s in (ent or {}).get("scores") or []][:reps]
                for i, s in enumerate(hit):
                    rows.setdefault(vid, {}).setdefault(case_key, []).append(
                        {
                            "variant_id": vid,
                            "rep": i + 1,
                            "score": s,
                            "ok": True,
                            "cached": True,
                        }
                    )
                cached_done += len(hit)
                # 命中不足 reps 的只补跑差额
                for r in range(len(hit) + 1, reps + 1):
                    tasks.append((v, c, r))
        with run.lock:
            run.total = len(variants) * len(cases) * reps
            run.done = cached_done
            run.cache_hits += cached_done
            run.updated_at = time.time()
        gen_dir = run_dir / f"gen{gen}"
        gen_dir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=max(1, min(int(p["workers"]), len(tasks) or 1))) as pool:
            futs = {
                pool.submit(
                    _eval_one_variant,
                    api_key=api_key,
                    model=run.model,
                    case=case,
                    bank=bank,
                    variant=variant,
                    rep=rep,
                    abort=run._abort,
                    meter=run.token_meter,
                ): (str(variant["id"]), f"{case.get('suite')}/{case.get('id')}")
                for variant, case, rep in tasks
            }
            for fut in as_completed(futs):
                if run._abort.is_set():
                    break
                vid, case_key = futs[fut]
                try:
                    row = fut.result()
                except Exception as e:  # noqa: BLE001
                    row = {"variant_id": vid, "score": None, "ok": False, "error": str(e)}
                if row.get("aborted"):
                    continue
                rows.setdefault(vid, {}).setdefault(case_key, []).append(row)
                with run.lock:
                    run.done += 1
                    run.updated_at = time.time()
        if use_cache:
            # 写回：每 (variant, case) 本轮新跑的分数并入本地评估缓存
            for variant in variants:
                vid = str(variant["id"])
                gh = gene_hash_of(variant)
                for case in cases:
                    case_key = f"{case.get('suite')}/{case.get('id')}"
                    fresh = [
                        float(r["score"])
                        for r in rows.get(vid, {}).get(case_key) or []
                        if not r.get("cached") and r.get("score") is not None
                    ]
                    if fresh:
                        cache_put(gh, run.model, case, fresh)
        scorecards: list[dict] = []
        for variant in variants:
            vid = str(variant["id"])
            per_case: list[dict] = []
            all_scores: list[float] = []
            total_fails = 0
            total_runs = 0
            for case in cases:
                case_key = f"{case.get('suite')}/{case.get('id')}"
                case_rows = rows.get(vid, {}).get(case_key) or []
                scores = [
                    float(r["score"]) for r in case_rows if r.get("score") is not None
                ]
                all_scores.extend(scores)
                # 失败 = 已执行但 score 为 None（裁判失败/异常）；缓存命中的分数同样算有效 run
                fails = len(case_rows) - len(scores)
                total_fails += fails
                total_runs += len(case_rows)
                per_case.append(
                    {
                        "suite": case.get("suite"),
                        "id": case.get("id"),
                        "level": case.get("level"),
                        "test_type": case.get("test_type") or case.get("dimension"),
                        "scores": scores,
                        "failures": fails,
                        "total_runs": len(case_rows),
                        "stats": calc_stats(scores),
                        "dimension_scores": _agg_dimension_scores(case_rows),
                    }
                )
            stats = calc_stats(all_scores)
            failure_rate = round(total_fails / total_runs, 4) if total_runs else None
            card = {
                "run_id": run.id,
                "gen": gen,
                "variant_id": vid,
                "title": variant.get("title") or vid,
                "hash": variant.get("hash"),
                "slots": dict(variant.get("slots") or {}),
                "reps": reps,
                "cases": per_case,
                **stats,
                "composite": composite(stats),
                "failures": total_fails,
                "total_runs": total_runs,
                "failure_rate": failure_rate,
                "unreliable": bool(failure_rate is not None and failure_rate > 0.5),
            }
            (gen_dir / f"scorecard_{vid}.json").write_text(
                json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            scorecards.append(card)
        with run.lock:
            for card in scorecards:
                st = run.failure_stats.setdefault(
                    str(card["variant_id"]), {"failed_runs": 0, "total_runs": 0}
                )
                st["failed_runs"] += int(card["failures"])
                st["total_runs"] += int(card["total_runs"])
            run.updated_at = time.time()
        return scorecards

    def _write_gen_summary(
        self,
        run_dir: Path,
        gen: int,
        scorecards: list[dict],
        ranked: list[dict],
        gate_row: dict,
    ) -> None:
        summaries = [
            {
                "variant_id": c["variant_id"],
                "title": c.get("title"),
                "n": c.get("n"),
                "mean": c.get("mean"),
                "sdv": c.get("sdv"),
                "composite": c.get("composite"),
                "failures": c.get("failures"),
                "total_runs": c.get("total_runs"),
                "unreliable": c.get("unreliable"),
            }
            for c in ranked
        ]
        summary = {
            "run_id": run_dir.name,
            "gen": gen,
            "ranking": summaries,
            "marks": pick_marks(
                [{**s, "variant_id": s["variant_id"]} for s in summaries]
            ),
            "gate": gate_row,
        }
        (run_dir / f"gen{gen}" / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _next_generation(
        self,
        run: EvolveRun,
        api_key: str,
        bank: dict,
        anchor: dict,
        scorecards: list[dict],
        ranked: list[dict],
        gen: int,
        mutation_level: str = "local",
    ) -> dict:
        """精英保留 + 交叉 + 随机移民 + LLM 精炼（local 邻域 / wide 大开角）→ 下一代 bank。"""
        p = run.params
        n = int(p["variants_per_gen"])
        elite_k = min(int(p["elite_k"]), len(ranked))
        elites = ranked[:elite_k]
        rng = random.Random(f"{run.id}:{gen}")

        next_variants: list[dict] = []
        elite_ids: list[str] = []
        for card in elites:
            v = _variant_of(bank, card["variant_id"])
            if v:
                next_variants.append(dict(v))
                elite_ids.append(str(v["id"]))

        needed = max(0, n - len(next_variants))
        # 随机移民：每代 1–2 个无种子随机重组 variant，防早熟（给交叉/精炼留位）
        n_imm = 0
        if needed >= 2:
            n_imm = 2 if needed >= 4 else 1
        rest = needed - n_imm
        n_cross = max(1, rest // 2) if rest > 1 else rest
        # 交叉：top 亲本轮转配对
        parents = [c["variant_id"] for c in ranked[: max(2, elite_k + 1)]]
        for i in range(min(n_cross, needed)):
            pa_id = parents[i % len(parents)]
            pb_id = parents[(i + 1) % len(parents)]
            pa = _variant_of(bank, pa_id)
            pb = _variant_of(bank, pb_id)
            if not pa or not pb:
                continue
            next_variants.append(
                crossover(bank, pa, pb, new_id=f"var.x{gen + 1}_{i}", rng=rng)
            )
        # 随机移民注入（来源可标识：role_in_demo="immigrant"）
        for i in range(min(n_imm, max(0, n - len(next_variants)))):
            next_variants.append(
                random_immigrant(bank, new_id=f"var.imm{gen + 1}_{i}", rng=rng)
            )
        needed = max(0, n - len(next_variants))

        refined_bank: dict = {"alleles": {}, "variants": []}
        if needed > 0:
            champion_card = elites[0]
            seed = _seed_from_variant(bank, champion_card["variant_id"])
            failure = attribute_failure(
                [c for c in scorecards if c["variant_id"] == champion_card["variant_id"]]
            )
            with run.token_meter.activate():
                refined_bank = refine_genomes(
                    api_key,
                    run.model,
                    anchor,
                    seed,
                    failure_notes=failure["failure_notes"],
                    mode=mutation_level,
                )
            for v in refined_bank.get("variants") or []:
                if needed <= 0:
                    break
                vid = str(v.get("id") or "")
                if not vid or vid in elite_ids:
                    continue
                if any(str(x.get("id")) == vid for x in next_variants):
                    continue
                next_variants.append(dict(v))
                needed -= 1

        merged = _merge_banks(bank, refined_bank, next_variants, n)
        # 进化算子记录（report 可解释：本代变异档位 + 移民来源）
        merged.setdefault("meta", {})["evolve_ops"] = {
            "gen": gen + 1,
            "mutation_level": mutation_level,
            "immigrants": [
                str(v.get("id"))
                for v in next_variants
                if v.get("role_in_demo") == "immigrant"
            ],
        }
        return merged

    def _final_holdout(
        self,
        run: EvolveRun,
        api_key: str,
        best: dict,
        holdout_cases: list[dict],
        run_dir: Path,
    ) -> dict[str, Any]:
        """总冠军在 holdout 集上跑 final_reps 次终验。"""
        reps = int(run.params["final_reps"])
        variant = best["variant"]
        bank = best["bank"]
        rows: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=int(run.params["workers"])) as pool:
            futs = {
                pool.submit(
                    _eval_one_variant,
                    api_key=api_key,
                    model=run.model,
                    case=case,
                    bank=bank,
                    variant=variant,
                    rep=r,
                    abort=run._abort,
                    meter=run.token_meter,
                ): f"{case.get('suite')}/{case.get('id')}"
                for case in holdout_cases
                for r in range(1, reps + 1)
            }
            for fut in as_completed(futs):
                if run._abort.is_set():
                    break
                case_key = futs[fut]
                try:
                    row = fut.result()
                except Exception as e:  # noqa: BLE001
                    row = {"score": None, "ok": False, "error": str(e)}
                if row.get("aborted"):
                    continue
                rows.setdefault(case_key, []).append(row)
        per_case: list[dict] = []
        all_scores: list[float] = []
        for case in holdout_cases:
            case_key = f"{case.get('suite')}/{case.get('id')}"
            case_rows = rows.get(case_key) or []
            scores = [float(r["score"]) for r in case_rows if r.get("score") is not None]
            all_scores.extend(scores)
            per_case.append(
                {
                    "suite": case.get("suite"),
                    "id": case.get("id"),
                    "level": case.get("level"),
                    "scores": scores,
                    "stats": calc_stats(scores),
                    "dimension_scores": _agg_dimension_scores(case_rows),
                }
            )
        stats = calc_stats(all_scores)
        card = {
            "run_id": run.id,
            "variant_id": best["variant_id"],
            "reps": reps,
            "part": "holdout",
            "cases": per_case,
            **stats,
            "composite": composite(stats),
        }
        final_dir = run_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "holdout_scorecard.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "n": stats["n"],
            "mean": stats["mean"],
            "sdv": stats["sdv"],
            "composite": card["composite"],
        }

    def _final_baseline(
        self,
        run: EvolveRun,
        api_key: str,
        cases: list[dict],
        run_dir: Path,
    ) -> dict[str, Any]:
        """arm A 基线（host 原题）在 manifest.cases 上跑 eval_reps 次，作对照锚点。"""
        reps = int(run.params["eval_reps"])
        rows: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=int(run.params["workers"])) as pool:
            futs = {
                pool.submit(
                    _eval_one_baseline,
                    api_key=api_key,
                    model=run.model,
                    case=case,
                    rep=r,
                    abort=run._abort,
                    meter=run.token_meter,
                ): f"{case.get('suite')}/{case.get('id')}"
                for case in cases
                for r in range(1, reps + 1)
            }
            for fut in as_completed(futs):
                if run._abort.is_set():
                    break
                case_key = futs[fut]
                try:
                    row = fut.result()
                except Exception as e:  # noqa: BLE001
                    row = {"score": None, "ok": False, "error": str(e)}
                if row.get("aborted"):
                    continue
                rows.setdefault(case_key, []).append(row)
        per_case: list[dict] = []
        all_scores: list[float] = []
        for case in cases:
            case_key = f"{case.get('suite')}/{case.get('id')}"
            case_rows = rows.get(case_key) or []
            scores = [float(r["score"]) for r in case_rows if r.get("score") is not None]
            all_scores.extend(scores)
            per_case.append(
                {
                    "suite": case.get("suite"),
                    "id": case.get("id"),
                    "level": case.get("level"),
                    "scores": scores,
                    "stats": calc_stats(scores),
                }
            )
        stats = calc_stats(all_scores)
        card = {
            "run_id": run.id,
            "arm": "A",
            "reps": reps,
            "part": "cases",
            "cases": per_case,
            **stats,
            "composite": composite(stats),
        }
        final_dir = run_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "baseline_arm_a.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "arm": "A",
            "n": stats["n"],
            "mean": stats["mean"],
            "sdv": stats["sdv"],
            "composite": card["composite"],
        }

    def _build_report(
        self,
        run: EvolveRun,
        manifest: dict,
        best: dict,
        holdout_summary: dict | None,
        baseline_summary: dict | None,
        evolution_ops: list | None = None,
    ) -> dict[str, Any]:
        champ_mean = (best.get("scorecard") or {}).get("mean")
        gap = None
        if baseline_summary and baseline_summary.get("mean") is not None and champ_mean is not None:
            gap = round(float(champ_mean) - float(baseline_summary["mean"]), 2)
        wall = wall_by_stage(run.token_marks, run.created_at)
        return {
            "schema": "yiagent.factory.evolve_report",
            "version": 1,
            "run_id": run.id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "demand": run.demand,
            "model": run.model,
            "params": dict(run.params),
            "manifest": {
                "id": manifest.get("id"),
                "cases": len(manifest.get("cases") or []),
                "holdout": len(manifest.get("holdout") or []),
                "params": manifest.get("params") or {},
            },
            "champion_curve": list(run.champion_curve),
            "gates": list(run.gates),
            "evolution_ops": list(evolution_ops or []),
            "failure_rates": summarize_failures(run.failure_stats),
            "champion_stratified": stratify_scores(
                (best.get("scorecard") or {}).get("cases") or []
            ),
            "stop_reason": run.stop_reason,
            "champion": {
                "gen": best["gen"],
                "variant_id": best["variant_id"],
                "composite": best["composite"],
                "variant": best["variant"],
                "bank": best["bank"],
            },
            "baseline_arm_a": baseline_summary,
            "champion_minus_baseline_mean": gap,
            "holdout": holdout_summary,
            "token_usage": run.token_meter.summary(),
            "token_by_stage": [
                {"stage": run.token_marks[i]["stage"],
                 **_usage_delta(run.token_marks[i - 1]["usage"], run.token_marks[i]["usage"])}
                for i in range(1, len(run.token_marks))
            ],
            "wall_by_stage": wall,  # [{stage, seconds, pct}] 分阶段墙钟
            "wall_total_sec": round(sum(s["seconds"] for s in wall), 2),
            "eval_cache": {
                "hits": run.cache_hits,
                "note": "本地评估缓存命中次数＝跳过的 LLM 答题+裁判调用数",
            },
        }

    def _render_report_md(self, report: dict) -> str:
        lines = [
            f"# 进化报告 {report['run_id']}",
            "",
            f"- 需求：{report.get('demand') or ''}",
            f"- 模型：{report.get('model')}",
            f"- 停止原因：{report.get('stop_reason')}",
            "",
            "## 测试集",
            "",
            f"- manifest：`{report['manifest'].get('id')}` "
            f"（进化 {report['manifest'].get('cases')} 题 / holdout {report['manifest'].get('holdout')} 题）",
            "",
            "## 代际冠军曲线",
            "",
            "| 代 | variant | mean | sdv | composite |",
            "|---|---|---|---|---|",
        ]
        for row in report.get("champion_curve") or []:
            lines.append(
                f"| {row['gen']} | {row['variant_id']} | {row.get('mean')} | "
                f"{row.get('sdv')} | {row.get('composite')} |"
            )
        lines += ["", "## 门禁记录", ""]
        for g in report.get("gates") or []:
            lines.append(f"- gen{g['gen']}：{g['verdict']} — {g.get('reason')}")
        ops = report.get("evolution_ops") or []
        if ops:
            lines += ["", "## 进化算子", ""]
            for op in ops:
                level = "大开角重写" if op.get("mutation_level") == "wide" else "邻域精炼"
                imm = "、".join(f"`{i}`" for i in op.get("immigrants") or []) or "无"
                lines.append(
                    f"- gen{op.get('gen')}：变异档位 {level}"
                    f"（{op.get('mutation_level')}）· 随机移民 {imm}"
                )
        strat = report.get("champion_stratified") or {}
        lines += ["", "## 冠军分层均分（按题型/套件）", ""]
        if strat.get("method") == "none":
            lines.append(f"- {strat.get('note') or '无法分层'}")
        else:
            lines.append(f"- 分层依据：{strat.get('method')}")
            lines += ["", "| 层 | n | mean | sdv |", "|---|---|---|---|"]
            for key, st in (strat.get("layers") or {}).items():
                lines.append(
                    f"| {key} | {st.get('n')} | {st.get('mean')} | {st.get('sdv')} |"
                )
        fail = report.get("failure_rates") or {}
        glob = fail.get("global") or {}
        lines += [
            "",
            "## 评分失败率",
            "",
            f"- 全局：{glob.get('failed_runs')}/{glob.get('total_runs')} 失败"
            f"（rate {glob.get('rate')}）",
        ]
        for vid, row in (fail.get("by_variant") or {}).items():
            if not row.get("failed_runs") and not row.get("unreliable"):
                continue
            tag = " ⚠ unreliable（不参与精英/冠军评选）" if row.get("unreliable") else ""
            lines.append(
                f"- `{vid}`：{row.get('failed_runs')}/{row.get('total_runs')} 失败"
                f"（rate {row.get('rate')}）{tag}"
            )
        champ = report.get("champion") or {}
        lines += [
            "",
            "## 冠军基因组",
            "",
            f"- gen{champ.get('gen')} · `{champ.get('variant_id')}` · composite {champ.get('composite')}",
            f"- slots：`{json.dumps((champ.get('variant') or {}).get('slots') or {}, ensure_ascii=False)}`",
            "",
            "## A/C 对照与 holdout",
            "",
        ]
        base = report.get("baseline_arm_a")
        if base:
            lines.append(
                f"- arm A 基线：mean {base.get('mean')} / sdv {base.get('sdv')} / composite {base.get('composite')}"
            )
            gap = report.get("champion_minus_baseline_mean")
            if gap is not None:
                lines.append(f"- 冠军 mean − 基线 mean：{gap:+.2f}")
        else:
            lines.append("- arm A 基线：未运行")
        hold = report.get("holdout")
        if hold:
            lines.append(
                f"- holdout 终验：mean {hold.get('mean')} / sdv {hold.get('sdv')} / composite {hold.get('composite')}"
            )
        else:
            lines.append("- holdout 终验：未运行")
        usage = report.get("token_usage") or {}
        hit_rate = usage.get("cache_hit_rate")
        hit_txt = f"{hit_rate * 100:.1f}%" if isinstance(hit_rate, (int, float)) else "-"
        lines += [
            "",
            "## token 用量",
            "",
            f"- 总计：calls {usage.get('calls')} · 输入 {usage.get('prompt_tokens')}"
            f"（缓存命中 {usage.get('cached_tokens')}，命中率 {hit_txt}）"
            f" · 输出 {usage.get('completion_tokens')}"
            f" · 实际消耗估计 {usage.get('billable_estimate')}",
        ]
        cache = report.get("eval_cache") or {}
        if cache.get("hits"):
            lines.append(f"- 本地评估缓存：命中 {cache['hits']} 次（跳过的 LLM 调用）")
        stages = report.get("token_by_stage") or []
        if stages:
            lines += [
                "",
                "| 阶段 | calls | 输入 | 缓存命中 | 输出 | 实际消耗估计 |",
                "|---|---|---|---|---|---|",
            ]
            for s in stages:
                lines.append(
                    f"| {s.get('stage')} | {s.get('calls')} | {s.get('prompt_tokens')} | "
                    f"{s.get('cached_tokens')} | {s.get('completion_tokens')} | "
                    f"{s.get('billable_estimate')} |"
                )
        wall = report.get("wall_by_stage") or []
        if wall:
            lines += [
                "",
                "## 耗时分布",
                "",
                f"- 总墙钟：{report.get('wall_total_sec')} 秒（阶段耗时 = 相邻阶段快照时间戳差值）",
                "",
                "| 阶段 | 耗时（秒） | 占比 |",
                "|---|---|---|",
            ]
            for s in wall:
                pct = s.get("pct")
                lines.append(
                    f"| {s.get('stage')} | {s.get('seconds')} | "
                    f"{f'{pct}%' if pct is not None else '-'} |"
                )
        purposes = (usage.get("by_purpose") or {})
        if purposes:
            lines += [
                "",
                "| 用途 | calls | 输入 | 缓存命中 | 输出 | 实际消耗估计 |",
                "|---|---|---|---|---|---|",
            ]
            for name, b in purposes.items():
                lines.append(
                    f"| {name} | {b.get('calls')} | {b.get('prompt_tokens')} | "
                    f"{b.get('cached_tokens')} | {b.get('completion_tokens')} | "
                    f"{b.get('billable_estimate')} |"
                )
        lines.append("")
        return "\n".join(lines)


EVOLVE_MANAGER = EvolveManager()
