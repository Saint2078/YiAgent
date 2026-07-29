"""Session-based factory pipeline: case → baseline A/B → genomes → prefilter → champion."""

from __future__ import annotations

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
    variant_map,
)
from generate import (
    bank_from_improve_seed,
    format_criteria_text,
    format_target_text,
    generate_case,
    generate_genomes,
    normalize_case,
    parse_criteria_text,
    parse_target_text,
    refine_genomes,
)
from judge import judge_with_retries
from llm_client import chat_completions, extract_content
from run_log import get_or_create_log
from token_meter import TokenMeter
from case_library import LIBRARY

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
SAVE = ROOT / "save"

BASELINE_ARMS = (
    {"id": "A", "title": "A · 原题对照"},
    {"id": "B", "title": "B · 灌入完整评分标准"},
)


def load_json(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def calc_stats(scores: list[float]) -> dict[str, Any]:
    if not scores:
        return {"n": 0, "min": None, "max": None, "mean": None, "sdv": None}
    n = len(scores)
    mean = statistics.mean(scores)
    sdv = statistics.stdev(scores) if n >= 2 else 0.0
    return {
        "n": n,
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "mean": round(mean, 2),
        "sdv": round(sdv, 2),
    }


def pick_marks(summaries: list[dict]) -> dict[str, str | None]:
    """效果最优 / 稳定最优 / 均衡最优 → variant_id."""
    scored = [s for s in summaries if s.get("mean") is not None]
    if not scored:
        return {"perf": None, "stable": None, "balanced": None}

    perf = max(scored, key=lambda s: (s["mean"], -(s.get("sdv") or 99)))
    stable_cands = [s for s in scored if s.get("n", 0) >= 2]
    if not stable_cands:
        stable_cands = scored
    stable = min(stable_cands, key=lambda s: (s.get("sdv") if s.get("sdv") is not None else 99, -s["mean"]))
    balanced = max(
        scored,
        key=lambda s: (s["mean"] - 1.5 * (s.get("sdv") or 0), s["mean"]),
    )
    return {
        "perf": perf["variant_id"],
        "stable": stable["variant_id"],
        "balanced": balanced["variant_id"],
    }


@dataclass
class Session:
    id: str
    model: str = "k3"
    phase: str = "idle"
    # idle|case_ready|baselining|baseline_done|genomes_ready|prefiltering|prefilter_done|championing|done|error
    oral: str = ""
    case: dict | None = None
    bank: dict | None = None
    target_text: str = ""
    criteria_text: str = ""
    pass_mean: float = 70.0
    qualify_target: int = 3
    baseline_reps: int = 5
    pre_reps: int = 3
    champ_reps: int = 5
    workers: int = 4
    baseline_scores: dict[str, list[float]] = field(default_factory=dict)
    pre_scores: dict[str, list[float]] = field(default_factory=dict)
    champ_scores: dict[str, list[float]] = field(default_factory=dict)
    pool: list[str] = field(default_factory=list)
    logs: list[dict] = field(default_factory=list)
    status: str = "idle"  # idle|running|done|aborted|error|skipped
    total: int = 0
    done: int = 0
    qualified_count: int = 0
    early_stopped: bool = False
    marks: dict[str, str | None] = field(default_factory=dict)
    error: str | None = None
    frozen_demo: bool = False
    baseline_stale: bool = False
    auto: bool = False
    auto_step: str | None = None
    # case|baseline|genomes|prefilter|champion|save|done
    champion_mark: str = "balanced"
    best_genome: dict[str, Any] | None = None
    auto_save: dict[str, Any] | None = None
    improve_mode: bool = False
    seed_variant_id: str | None = None
    improve_pack: dict[str, Any] | None = None
    token_meter: TokenMeter = field(default_factory=TokenMeter)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    _abort: threading.Event = field(default_factory=threading.Event)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            pre_sum = self._summaries(self.pre_scores, self.pass_mean)
            champ_sum = self._summaries(self.champ_scores, self.pass_mean)
            baseline_sum = self._baseline_summaries()
            variants = []
            if self.bank:
                for v in self.bank.get("variants") or []:
                    variants.append(
                        {
                            "id": v["id"],
                            "title": v.get("title") or v["id"],
                            "slots": v.get("slots") or {},
                            "hash": v.get("hash"),
                        }
                    )
            token_usage = self.token_meter.summary()
            return {
                "id": self.id,
                "phase": self.phase,
                "status": self.status,
                "model": self.model,
                "oral": self.oral,
                "case": self.case,
                "target_text": self.target_text,
                "criteria_text": self.criteria_text,
                "variants": variants,
                "pass_mean": self.pass_mean,
                "qualify_target": self.qualify_target,
                "baseline_reps": self.baseline_reps,
                "pre_reps": self.pre_reps,
                "champ_reps": self.champ_reps,
                "workers": self.workers,
                "total": self.total,
                "done": self.done,
                "qualified_count": self.qualified_count,
                "early_stopped": self.early_stopped,
                "baseline_summaries": baseline_sum,
                "baseline_stale": self.baseline_stale,
                "pre_summaries": pre_sum,
                "champ_summaries": champ_sum,
                "pool": list(self.pool),
                "marks": dict(self.marks),
                "logs": list(self.logs)[:80],
                "error": self.error,
                "frozen_demo": self.frozen_demo,
                "auto": self.auto,
                "auto_step": self.auto_step,
                "champion_mark": self.champion_mark,
                "best_genome": dict(self.best_genome) if self.best_genome else None,
                "auto_save": dict(self.auto_save) if self.auto_save else None,
                "improve_mode": self.improve_mode,
                "seed_variant_id": self.seed_variant_id,
                "token_usage": token_usage,
                "updated_at": self.updated_at,
            }

    def _baseline_summaries(self) -> list[dict]:
        out = []
        for arm in BASELINE_ARMS:
            aid = arm["id"]
            st = calc_stats(self.baseline_scores.get(aid) or [])
            out.append(
                {
                    "arm": aid,
                    "variant_id": aid,
                    "title": arm["title"],
                    **st,
                    "composite": round(st["mean"] - 1.5 * (st["sdv"] or 0), 2)
                    if st["mean"] is not None
                    else None,
                }
            )
        means = {r["arm"]: r["mean"] for r in out if r.get("mean") is not None}
        if "A" in means and "B" in means:
            gap = round(means["B"] - means["A"], 2)
            for r in out:
                r["gap_b_minus_a"] = gap
        return out

    def _summaries(self, scores_by: dict[str, list[float]], pass_mean: float) -> list[dict]:
        out = []
        for vid, scores in scores_by.items():
            st = calc_stats(scores)
            passed = st["mean"] is not None and st["mean"] >= pass_mean
            title = vid
            if self.bank:
                for v in self.bank.get("variants") or []:
                    if v["id"] == vid:
                        title = v.get("title") or vid
                        break
            out.append(
                {
                    "variant_id": vid,
                    "title": title,
                    **st,
                    "passed": passed,
                    "composite": round(st["mean"] - 1.5 * (st["sdv"] or 0), 2)
                    if st["mean"] is not None
                    else None,
                }
            )
        out.sort(key=lambda x: (-(x["mean"] or 0), x.get("sdv") or 99))
        return out


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        # fixtures kept for demo hydrate
        self.fixture_bank = load_json(FIX / "alleles" / "bank.json")
        self.fixture_case = load_json(FIX / "cases" / "l_criticalthinking_059_basic.json")

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def _log_case(self, sess: Session) -> None:
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        case = sess.case or {}
        rlog.record_case(
            oral=sess.oral,
            case=case,
            target_text=sess.target_text,
            criteria_text=sess.criteria_text,
            judge=judge_body(case) if case else None,
        )
        rlog.record_phase(sess.phase)

    def create_case(self, *, api_key: str, model: str, oral: str) -> Session:
        meter = TokenMeter()
        with meter.activate():
            case = generate_case(api_key, model, oral)
        sess = Session(
            id=uuid.uuid4().hex[:12],
            model=model,
            phase="case_ready",
            oral=oral.strip(),
            case=case,
            target_text=format_target_text(case),
            criteria_text=format_criteria_text(case),
            status="idle",
            token_meter=meter,
        )
        with self._lock:
            self._sessions[sess.id] = sess
        self._log_case(sess)
        return sess

    def load_library_case(
        self,
        *,
        suite: str,
        case_id: str,
        level: str = "basic",
        model: str = "k3",
    ) -> Session:
        """Load a ready-made case from case/xsct (no LLM call)."""
        factory_case = LIBRARY.to_factory_case(suite, case_id, level)
        oral = (
            f"[用例库] {factory_case.get('suite')}/{factory_case.get('id')} · "
            f"{factory_case.get('level')} · {factory_case.get('title')}"
        )
        case = normalize_case(factory_case, oral=oral)
        # preserve full message thread (multi-turn XSCT cases)
        msgs = factory_case.get("messages") or []
        if isinstance(msgs, list) and msgs:
            case["messages"] = [
                {"role": str(m.get("role")), "content": str(m.get("content") or "")}
                for m in msgs
                if isinstance(m, dict) and m.get("role")
            ]
        # preserve library metadata after normalize
        case["dimension"] = factory_case.get("dimension") or ""
        case["level"] = factory_case.get("level")
        case["suite"] = factory_case.get("suite")
        case["source"] = "xsct"
        case["description"] = factory_case.get("description") or ""
        if factory_case.get("reference_answer"):
            case["reference_answer"] = factory_case["reference_answer"]
        sess = Session(
            id=uuid.uuid4().hex[:12],
            model=model,
            phase="case_ready",
            oral=oral,
            case=case,
            target_text=format_target_text(case),
            criteria_text=format_criteria_text(case),
            status="idle",
            frozen_demo=False,
        )
        with self._lock:
            self._sessions[sess.id] = sess
        self._log_case(sess)
        return sess

    def hydrate_demo(self, *, fresh: bool = False) -> Session:
        """Load frozen demo pack unless fresh=True (manual live run from fixture case)."""
        if not fresh:
            pack_path = FIX / "demo_pack.json"
            if pack_path.is_file():
                return self._session_from_pack(load_json(pack_path), frozen=True)
        return self.seed_fixture_case(model="k3" if fresh else "demo")

    def seed_fixture_case(self, *, model: str = "k3") -> Session:
        case = normalize_case(dict(self.fixture_case), oral="演示：批判思维虚假二选一")
        sess = Session(
            id=uuid.uuid4().hex[:12],
            model=model,
            phase="case_ready",
            oral="演示：批判思维虚假二选一",
            case=case,
            bank=None,
            target_text=format_target_text(case),
            criteria_text=format_criteria_text(case),
            status="idle",
            frozen_demo=False,
        )
        with self._lock:
            self._sessions[sess.id] = sess
        self._log_case(sess)
        return sess

    def start_demo_live(
        self,
        *,
        api_key: str,
        model: str = "k3",
        baseline_reps: int = 5,
        workers: int = 4,
    ) -> Session:
        """Seed critical-thinking fixture case and immediately start A/B baseline (real run)."""
        sess = self.seed_fixture_case(model=model)
        return self.start_baseline(
            sess.id,
            api_key=api_key,
            baseline_reps=baseline_reps,
            workers=workers,
            model=model,
        )

    def attach_fixture_bank(self, session_id: str) -> Session:
        sess = self._require(session_id)
        with sess.lock:
            if sess.status == "running":
                raise ValueError("already running")
            sess.bank = dict(self.fixture_bank)
            if sess.phase in ("case_ready", "baseline_done"):
                sess.phase = "genomes_ready"
            sess.updated_at = time.time()
            bank = sess.bank
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        rlog.record_genomes(bank=bank)
        rlog.record_phase("genomes_ready", note="fixture_bank")
        return sess

    def export_pack(self, session_id: str) -> dict[str, Any]:
        sess = self._require(session_id)
        with sess.lock:
            phase = sess.phase
            if phase in ("baselining", "prefiltering", "championing"):
                raise ValueError(f"busy: {phase}")
            return {
                "version": 1,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "oral": sess.oral,
                "phase": phase,
                "model": "demo",
                "source_model": sess.model,
                "case": sess.case,
                "target_text": sess.target_text,
                "criteria_text": sess.criteria_text,
                "bank": sess.bank,
                "baseline_reps": sess.baseline_reps,
                "baseline_scores": {k: list(v) for k, v in sess.baseline_scores.items()},
                "pre_reps": sess.pre_reps,
                "pre_scores": {k: list(v) for k, v in sess.pre_scores.items()},
                "champ_reps": sess.champ_reps,
                "champ_scores": {k: list(v) for k, v in sess.champ_scores.items()},
                "pass_mean": sess.pass_mean,
                "qualify_target": sess.qualify_target,
                "qualified_count": sess.qualified_count,
                "early_stopped": sess.early_stopped,
                "pool": list(sess.pool),
                "marks": dict(sess.marks),
                "token_usage": sess.token_meter.summary(),
            }

    def save_session(
        self,
        session_id: str,
        *,
        freeze_demo: bool = False,
        label: str = "session",
        version_tag: str = "v1.0",
    ) -> dict[str, Any]:
        """Write pack + run log under save/; optionally freeze fixtures/demo_pack.json."""
        import json

        pack = self.export_pack(session_id)
        sess = self._require(session_id)
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        # Refresh summaries into log if phases already done but events missing.
        with sess.lock:
            if sess.baseline_scores or sess.status == "skipped":
                rlog.record_baseline(
                    scores=sess.baseline_scores,
                    summaries=sess._baseline_summaries(),
                    reps=sess.baseline_reps,
                    skipped=sess.status == "skipped" and not sess.baseline_scores,
                )
            if sess.bank:
                rlog.record_genomes(bank=sess.bank)
            if sess.pre_scores:
                rlog.record_prefilter(
                    scores=sess.pre_scores,
                    summaries=sess._summaries(sess.pre_scores, sess.pass_mean),
                    pool=sess.pool,
                    pass_mean=sess.pass_mean,
                    qualify_target=sess.qualify_target,
                    qualified_count=sess.qualified_count,
                    early_stopped=sess.early_stopped,
                    reps=sess.pre_reps,
                )
            if sess.champ_scores:
                rlog.record_champion(
                    scores=sess.champ_scores,
                    summaries=sess._summaries(sess.champ_scores, sess.pass_mean),
                    pool=sess.pool,
                    marks=sess.marks,
                    reps=sess.champ_reps,
                )
            rlog.record_phase(sess.phase, note="save")
            rlog.model = sess.model
            rlog.oral = sess.oral
            rlog.token_usage = sess.token_meter.summary()

        SAVE.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        pack_path = SAVE / f"{stamp}_{label}_{session_id}_{version_tag}.json"
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
        log_path = rlog.write_local(label=f"{label}_log", version_tag=version_tag)
        ship = rlog.ship_to_server()  # stub — no send yet

        demo_path = None
        if freeze_demo:
            demo_path = FIX / "demo_pack.json"
            demo_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "pack_path": str(pack_path.relative_to(ROOT)),
            "log_path": str(log_path.relative_to(ROOT)),
            "demo_pack": str(demo_path.relative_to(ROOT)) if demo_path else None,
            "ship": ship,
            "phase": pack.get("phase"),
            "baseline_summaries": sess.snapshot().get("baseline_summaries"),
        }

    def _session_from_pack(self, pack: dict, *, frozen: bool) -> Session:
        case = pack.get("case") or normalize_case(
            dict(self.fixture_case), oral=pack.get("oral") or "演示：批判思维虚假二选一"
        )
        sess = Session(
            id=uuid.uuid4().hex[:12],
            model="demo" if frozen else (pack.get("source_model") or "k3"),
            phase=pack.get("phase") or "case_ready",
            oral=pack.get("oral") or "演示：批判思维虚假二选一",
            case=case,
            bank=pack.get("bank"),
            target_text=pack.get("target_text") or format_target_text(case),
            criteria_text=pack.get("criteria_text") or format_criteria_text(case),
            status="idle",
            baseline_reps=int(pack.get("baseline_reps") or 5),
            baseline_scores={k: list(v) for k, v in (pack.get("baseline_scores") or {}).items()},
            pre_reps=int(pack.get("pre_reps") or 3),
            pre_scores={k: list(v) for k, v in (pack.get("pre_scores") or {}).items()},
            champ_reps=int(pack.get("champ_reps") or 5),
            champ_scores={k: list(v) for k, v in (pack.get("champ_scores") or {}).items()},
            pass_mean=float(pack.get("pass_mean") or 70),
            qualify_target=int(pack.get("qualify_target") or 3),
            qualified_count=int(pack.get("qualified_count") or 0),
            early_stopped=bool(pack.get("early_stopped")),
            pool=list(pack.get("pool") or []),
            marks=dict(pack.get("marks") or {}),
            frozen_demo=frozen,
        )
        with self._lock:
            self._sessions[sess.id] = sess
        return sess

    def update_case_texts(
        self, session_id: str, *, target_text: str | None = None, criteria_text: str | None = None
    ) -> Session:
        sess = self._require(session_id)
        with sess.lock:
            changed = False
            if target_text is not None and target_text != sess.target_text:
                sess.target_text = target_text
                sess.case = parse_target_text(target_text, sess.case)
                changed = True
            if criteria_text is not None and criteria_text != sess.criteria_text:
                sess.criteria_text = criteria_text
                sess.case = parse_criteria_text(criteria_text, sess.case)
                changed = True
            # Keep A/B scores visible after later steps; only mark stale if texts changed.
            # Scores are cleared when the user explicitly re-runs baseline.
            if changed and sess.baseline_scores:
                sess.baseline_stale = True
            sess.updated_at = time.time()
        if changed:
            self._log_case(sess)
        return sess

    def skip_baseline(self, session_id: str) -> Session:
        """Allow proceeding to genomes without running A/B baseline."""
        sess = self._require(session_id)
        with sess.lock:
            if not sess.case:
                raise ValueError("case missing")
            if sess.status == "running":
                raise ValueError("already running")
            sess.baseline_scores = {}
            sess.phase = "baseline_done"
            sess.status = "skipped"
            sess.error = None
            sess.updated_at = time.time()
            reps = sess.baseline_reps
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        rlog.record_baseline(scores={}, summaries=sess._baseline_summaries(), reps=reps, skipped=True)
        rlog.record_phase("baseline_done", note="skipped")
        return sess

    def start_baseline(
        self,
        session_id: str,
        *,
        api_key: str,
        baseline_reps: int = 5,
        workers: int = 4,
        model: str | None = None,
    ) -> Session:
        sess = self._require(session_id)
        if not sess.case:
            raise ValueError("case missing")
        with sess.lock:
            if sess.status == "running":
                raise ValueError("already running")
            if model:
                sess.model = model
            sess.case = parse_target_text(sess.target_text, sess.case)
            sess.case = parse_criteria_text(sess.criteria_text, sess.case)
            sess.baseline_reps = max(1, min(int(baseline_reps), 10))
            sess.workers = max(1, min(int(workers), 12))
            sess.baseline_scores = {}
            sess.baseline_stale = False
            sess.done = 0
            sess.total = len(BASELINE_ARMS) * sess.baseline_reps
            sess.phase = "baselining"
            sess.status = "running"
            sess.error = None
            sess._abort.clear()
            # Keep non-baseline logs if any; drop old baseline rows.
            sess.logs = [l for l in sess.logs if l.get("stage") != "baseline"]
            case = dict(sess.case)
            reps = sess.baseline_reps
            workers_n = sess.workers
            m = sess.model
        threading.Thread(
            target=self._run_baseline,
            args=(sess, api_key, case, reps, workers_n, m),
            daemon=True,
        ).start()
        return sess

    def generate_genomes(self, session_id: str, *, api_key: str, model: str | None = None) -> Session:
        sess = self._require(session_id)
        if not sess.case:
            raise ValueError("case missing")
        with sess.lock:
            if model:
                sess.model = model
            # apply latest text edits
            sess.case = parse_target_text(sess.target_text, sess.case)
            sess.case = parse_criteria_text(sess.criteria_text, sess.case)
            case = dict(sess.case)
            m = sess.model
            meter = sess.token_meter
        with meter.activate():
            bank = generate_genomes(api_key, m, case)
        with sess.lock:
            sess.bank = bank
            sess.phase = "genomes_ready"
            sess.pre_scores.clear()
            sess.champ_scores.clear()
            sess.pool = []
            sess.logs = [l for l in sess.logs if l.get("stage") == "baseline"]
            sess.marks = {}
            sess.qualified_count = 0
            sess.early_stopped = False
            sess.error = None
            sess.status = "idle"
            sess.updated_at = time.time()
            bank_snap = bank
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        rlog.record_genomes(bank=bank_snap)
        rlog.record_phase("genomes_ready")
        return sess

    def load_seed_pack(self, pack: dict, *, model: str = "k3") -> Session:
        """Load improve-pack / best_genome → Session at genomes_ready (skip baseline)."""
        if not isinstance(pack, dict):
            raise ValueError("pack must be an object")

        # Normalize shapes
        if pack.get("kind") == "yiagent.improve_pack" or (pack.get("seed") and pack.get("case")):
            seed = pack.get("seed") or {}
            case = pack.get("case") or {}
            oral = str(pack.get("oral") or case.get("title") or "improve")
            transcript = pack.get("transcript") or []
            failure_notes = str(pack.get("failure_notes") or "")
            source_model = pack.get("model") or model
        elif pack.get("slot_texts") or (pack.get("variant_id") and pack.get("slots")):
            seed = {
                "variant_id": pack.get("variant_id"),
                "title": pack.get("title"),
                "hash": pack.get("hash"),
                "slots": pack.get("slots") or {},
                "slot_texts": pack.get("slot_texts") or {},
                "skills": pack.get("skills") or [],
            }
            case = pack.get("case") if isinstance(pack.get("case"), dict) else {}
            if not case.get("messages"):
                case = {
                    "id": case.get("id") or f"improve_{uuid.uuid4().hex[:8]}",
                    "title": case.get("title") or seed.get("title") or "改进鉴定",
                    "description": case.get("description") or "由 improve-pack / best_genome 载入",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是已装载 G1–G5 基因组的选手。按基因行事完成用户任务。",
                        },
                        {
                            "role": "user",
                            "content": str(pack.get("oral") or "请改进回答质量，对齐用户目标。"),
                        },
                    ],
                    "requirements": list(case.get("requirements") or ["对齐用户目标", "不编造", "结构清晰"]),
                    "criteria": case.get("criteria")
                    or {
                        "任务完成度": {
                            "weight": 40,
                            "desc": "是否直接回应用户目标",
                            "rubric": {
                                "90-100": "完整对齐",
                                "70-89": "大体完成",
                                "60-69": "部分完成",
                                "0-59": "跑偏",
                            },
                        },
                        "边界与诚实": {
                            "weight": 30,
                            "desc": "不编造",
                            "rubric": {
                                "90-100": "无编造",
                                "70-89": "偶有含糊",
                                "60-69": "松",
                                "0-59": "编造",
                            },
                        },
                        "结构清晰": {
                            "weight": 30,
                            "desc": "可操作性",
                            "rubric": {
                                "90-100": "清晰",
                                "70-89": "可读",
                                "60-69": "散乱",
                                "0-59": "难懂",
                            },
                        },
                    },
                }
            oral = str(pack.get("oral") or case.get("title") or "improve")
            transcript = pack.get("transcript") or []
            failure_notes = str(pack.get("failure_notes") or "")
            source_model = pack.get("model") or model
            pack = {
                "kind": "yiagent.improve_pack",
                "version": 1,
                "oral": oral,
                "case": case,
                "seed": seed,
                "transcript": transcript,
                "failure_notes": failure_notes,
                "model": source_model,
                "session_id": pack.get("session_id"),
            }
        else:
            raise ValueError("unrecognized pack: need yiagent.improve_pack or best_genome fields")

        if not isinstance(case, dict) or not case.get("messages"):
            raise ValueError("pack.case.messages required")
        if not isinstance(seed, dict) or not (seed.get("slots") or seed.get("slot_texts")):
            raise ValueError("pack.seed slots/slot_texts required")

        bank = bank_from_improve_seed(seed, case)
        seed_vid = str(seed.get("variant_id") or (bank.get("variants") or [{}])[0].get("id") or "var.seed")
        sess = Session(
            id=uuid.uuid4().hex[:12],
            model=str(source_model or model or "k3"),
            phase="genomes_ready",
            oral=oral,
            case=case,
            bank=bank,
            target_text=format_target_text(case),
            criteria_text=format_criteria_text(case),
            status="idle",
            improve_mode=True,
            seed_variant_id=seed_vid,
            improve_pack=pack,
        )
        with self._lock:
            self._sessions[sess.id] = sess
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        rlog.record_genomes(bank=bank)
        rlog.record_phase("genomes_ready", note="load-seed")
        return sess

    def refine_session_genomes(
        self, session_id: str, *, api_key: str, model: str | None = None
    ) -> Session:
        sess = self._require(session_id)
        if not sess.case:
            raise ValueError("case missing")
        with sess.lock:
            if model:
                sess.model = model
            sess.case = parse_target_text(sess.target_text, sess.case)
            sess.case = parse_criteria_text(sess.criteria_text, sess.case)
            case = dict(sess.case)
            m = sess.model
            meter = sess.token_meter
            pack = dict(sess.improve_pack) if sess.improve_pack else {}
            bank = sess.bank
            seed_vid = sess.seed_variant_id

        seed = pack.get("seed") if isinstance(pack.get("seed"), dict) else None
        if not seed and bank:
            # Rebuild seed from current bank seed variant
            vid = seed_vid or ((bank.get("variants") or [{}])[0].get("id"))
            variant = None
            for v in bank.get("variants") or []:
                if v.get("id") == vid:
                    variant = v
                    break
            if not variant and bank.get("variants"):
                variant = bank["variants"][0]
            if not variant:
                raise ValueError("no seed genome to refine — load improve-pack first")
            slots = dict(variant.get("slots") or {})
            alleles = bank.get("alleles") or {}
            slot_texts: dict[str, Any] = {}
            for slot, allele_id in slots.items():
                allele = None
                for a in alleles.get(slot) or []:
                    if a.get("id") == allele_id:
                        allele = {
                            "id": a.get("id"),
                            "label": a.get("label"),
                            "text": a.get("text"),
                        }
                        break
                slot_texts[slot] = {"allele_id": allele_id, "allele": allele}
            seed = {
                "variant_id": variant.get("id"),
                "title": variant.get("title"),
                "hash": variant.get("hash"),
                "slots": slots,
                "slot_texts": slot_texts,
                "skills": variant.get("skills") or [],
            }

        if not seed:
            raise ValueError("no seed genome to refine — load improve-pack first")

        with meter.activate():
            new_bank = refine_genomes(
                api_key,
                m,
                case,
                seed,
                transcript=pack.get("transcript") or [],
                failure_notes=str(pack.get("failure_notes") or ""),
            )
        with sess.lock:
            sess.bank = new_bank
            sess.phase = "genomes_ready"
            sess.pre_scores.clear()
            sess.champ_scores.clear()
            sess.pool = []
            sess.logs = [l for l in sess.logs if l.get("stage") == "baseline"]
            sess.marks = {}
            sess.qualified_count = 0
            sess.early_stopped = False
            sess.improve_mode = True
            sess.seed_variant_id = str(seed.get("variant_id") or sess.seed_variant_id)
            if not sess.improve_pack:
                sess.improve_pack = {
                    "kind": "yiagent.improve_pack",
                    "seed": seed,
                    "case": case,
                    "oral": sess.oral,
                    "transcript": [],
                    "failure_notes": "",
                }
            sess.error = None
            sess.status = "idle"
            sess.updated_at = time.time()
            bank_snap = new_bank
        rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
        rlog.record_genomes(bank=bank_snap)
        rlog.record_phase("genomes_ready", note="refine")
        return sess

    def start_improve_auto(
        self,
        *,
        api_key: str,
        pack: dict,
        model: str = "k3",
        pre_reps: int = 3,
        champ_reps: int = 5,
        qualify_target: int = 3,
        pass_mean: float = 70.0,
        workers: int = 4,
        champion_mark: str = "balanced",
        do_save: bool = True,
        skip_refine: bool = False,
    ) -> Session:
        """load-seed → refine → prefilter → champion → best genome."""
        mark = (champion_mark or "balanced").strip().lower()
        if mark not in ("perf", "stable", "balanced"):
            raise ValueError("champion_mark must be perf|stable|balanced")
        sess = self.load_seed_pack(pack, model=model)
        with sess.lock:
            sess.auto = True
            sess.auto_step = "genomes"
            sess.champion_mark = mark
            sess.best_genome = None
            sess.auto_save = None
            sess.pre_reps = max(1, min(int(pre_reps), 10))
            sess.champ_reps = max(1, min(int(champ_reps), 10))
            sess.qualify_target = max(1, min(int(qualify_target), 20))
            sess.pass_mean = float(pass_mean)
            sess.workers = max(1, min(int(workers), 12))
            sess.error = None
            sess._abort.clear()
            sess.updated_at = time.time()
        threading.Thread(
            target=self._run_improve_auto,
            args=(sess, api_key, bool(do_save), bool(skip_refine)),
            daemon=True,
        ).start()
        return sess

    def _run_improve_auto(
        self, sess: Session, api_key: str, do_save: bool, skip_refine: bool
    ) -> None:
        try:
            if not skip_refine:
                self._set_auto_step(sess, "genomes")
                self.refine_session_genomes(sess.id, api_key=api_key, model=sess.model)

            if sess._abort.is_set():
                return

            self._set_auto_step(sess, "prefilter")
            self.start_prefilter(
                sess.id,
                api_key=api_key,
                pre_reps=sess.pre_reps,
                qualify_target=sess.qualify_target,
                pass_mean=sess.pass_mean,
                workers=sess.workers,
            )
            if not self._wait_job(sess):
                return

            if sess._abort.is_set():
                return

            self._ensure_champion_pool(sess)

            self._set_auto_step(sess, "champion")
            self.start_champion(
                sess.id,
                api_key=api_key,
                champ_reps=sess.champ_reps,
                workers=sess.workers,
            )
            if not self._wait_job(sess):
                return

            if sess._abort.is_set():
                return

            mark = sess.champion_mark
            best = self._extract_best_genome(sess, mark)
            # Enrich for CLI apply
            with sess.lock:
                pack = dict(sess.improve_pack) if sess.improve_pack else {}
                case_full = dict(sess.case or {})
            best["case"] = {
                **(best.get("case") or {}),
                "messages": case_full.get("messages"),
                "requirements": case_full.get("requirements"),
                "criteria": case_full.get("criteria"),
                "description": case_full.get("description"),
            }
            if pack.get("transcript"):
                best["transcript"] = pack.get("transcript")
            if pack.get("failure_notes"):
                best["failure_notes"] = pack.get("failure_notes")
            # attach allele bank for richer apply
            with sess.lock:
                if sess.bank:
                    best["bank"] = sess.bank

            with sess.lock:
                sess.best_genome = best
                sess.updated_at = time.time()

            save_info: dict[str, Any] = {}
            if do_save:
                self._set_auto_step(sess, "save")
                import json

                SAVE.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
                best_path = SAVE / f"{stamp}_best_genome_{sess.id}_v1.0.json"
                best_path.write_text(
                    json.dumps(best, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                saved = self.save_session(
                    sess.id, freeze_demo=False, label="improve", version_tag="v1.0"
                )
                save_info = {
                    "best_genome_path": str(best_path.relative_to(ROOT)),
                    "pack_path": saved.get("pack_path"),
                    "log_path": saved.get("log_path"),
                }

            with sess.lock:
                sess.auto_save = save_info or None
                sess.auto_step = "done"
                sess.phase = "done"
                sess.status = "done"
                sess.updated_at = time.time()
            rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
            rlog.record_phase("done", note="improve-auto")
        except Exception as e:  # noqa: BLE001
            with sess.lock:
                sess.status = "error"
                sess.phase = "error"
                sess.auto_step = "error"
                sess.error = str(e)
                sess.updated_at = time.time()

    def start_prefilter(
        self,
        session_id: str,
        *,
        api_key: str,
        pre_reps: int = 3,
        qualify_target: int = 3,
        pass_mean: float = 70.0,
        workers: int = 4,
    ) -> Session:
        sess = self._require(session_id)
        if not sess.case or not sess.bank:
            raise ValueError("case/bank missing")
        with sess.lock:
            if sess.status == "running":
                raise ValueError("already running")
            sess.case = parse_target_text(sess.target_text, sess.case)
            sess.case = parse_criteria_text(sess.criteria_text, sess.case)
            sess.pre_reps = max(1, min(pre_reps, 10))
            sess.qualify_target = max(1, min(qualify_target, 20))
            sess.pass_mean = float(pass_mean)
            sess.workers = max(1, min(workers, 12))
            sess.pre_scores = {}
            sess.champ_scores = {}
            sess.pool = []
            sess.logs = [l for l in sess.logs if l.get("stage") == "baseline"]
            sess.marks = {}
            sess.qualified_count = 0
            sess.early_stopped = False
            sess.done = 0
            sess.total = 0
            sess.phase = "prefiltering"
            sess.status = "running"
            sess.error = None
            sess._abort.clear()
            case = dict(sess.case)
            bank = dict(sess.bank)
            reps = sess.pre_reps
            q_target = sess.qualify_target
            p_mean = sess.pass_mean
            workers_n = sess.workers
            model = sess.model
        variants = [v["id"] for v in bank.get("variants") or []]
        threading.Thread(
            target=self._run_prefilter,
            args=(sess, api_key, case, bank, variants, reps, q_target, p_mean, workers_n, model),
            daemon=True,
        ).start()
        return sess

    def set_pool(self, session_id: str, variant_ids: list[str]) -> Session:
        sess = self._require(session_id)
        with sess.lock:
            known = {v["id"] for v in (sess.bank or {}).get("variants") or []}
            sess.pool = [v for v in variant_ids if v in known]
            sess.updated_at = time.time()
            if sess.phase in ("prefilter_done", "done"):
                sess.phase = "prefilter_done"
        return sess

    def start_champion(
        self, session_id: str, *, api_key: str, champ_reps: int = 5, workers: int | None = None
    ) -> Session:
        sess = self._require(session_id)
        with sess.lock:
            if sess.status == "running":
                raise ValueError("already running")
            if not sess.pool:
                raise ValueError("empty champion pool")
            if not sess.case or not sess.bank:
                raise ValueError("case/bank missing")
            sess.champ_reps = max(1, min(champ_reps, 10))
            if workers is not None:
                sess.workers = max(1, min(workers, 12))
            sess.champ_scores = {}
            sess.marks = {}
            sess.done = 0
            sess.total = len(sess.pool) * sess.champ_reps
            sess.phase = "championing"
            sess.status = "running"
            sess.error = None
            sess._abort.clear()
            case = dict(sess.case)
            bank = dict(sess.bank)
            pool = list(sess.pool)
            reps = sess.champ_reps
            workers_n = sess.workers
            model = sess.model
        threading.Thread(
            target=self._run_champion,
            args=(sess, api_key, case, bank, pool, reps, workers_n, model),
            daemon=True,
        ).start()
        return sess

    def start_auto(
        self,
        *,
        api_key: str,
        model: str = "k3",
        source: str = "library",
        suite: str | None = None,
        case_id: str | None = None,
        level: str = "basic",
        oral: str | None = None,
        skip_baseline: bool = False,
        baseline_reps: int = 5,
        pre_reps: int = 3,
        champ_reps: int = 5,
        qualify_target: int = 3,
        pass_mean: float = 70.0,
        workers: int = 4,
        champion_mark: str = "balanced",
        do_save: bool = True,
    ) -> Session:
        """Unattended pipeline: case → A/B → genomes → prefilter → champion → best genome."""
        source = (source or "library").strip().lower()
        mark = (champion_mark or "balanced").strip().lower()
        if mark not in ("perf", "stable", "balanced"):
            raise ValueError("champion_mark must be perf|stable|balanced")

        if source == "library":
            if not suite or not case_id:
                raise ValueError("library source requires suite and id")
            sess = self.load_library_case(
                suite=suite.strip(),
                case_id=case_id.strip(),
                level=(level or "basic").strip(),
                model=model,
            )
        elif source == "oral":
            text = (oral or "").strip()
            if len(text) < 4:
                raise ValueError("oral source requires oral text")
            sess = self.create_case(api_key=api_key, model=model, oral=text)
        else:
            raise ValueError("source must be library|oral")

        with sess.lock:
            sess.auto = True
            sess.auto_step = "case"
            sess.champion_mark = mark
            sess.best_genome = None
            sess.auto_save = None
            sess.baseline_reps = max(1, min(int(baseline_reps), 10))
            sess.pre_reps = max(1, min(int(pre_reps), 10))
            sess.champ_reps = max(1, min(int(champ_reps), 10))
            sess.qualify_target = max(1, min(int(qualify_target), 20))
            sess.pass_mean = float(pass_mean)
            sess.workers = max(1, min(int(workers), 12))
            sess.error = None
            sess._abort.clear()
            sess.updated_at = time.time()

        threading.Thread(
            target=self._run_auto,
            args=(
                sess,
                api_key,
                bool(skip_baseline),
                bool(do_save),
            ),
            daemon=True,
        ).start()
        return sess

    def _set_auto_step(self, sess: Session, step: str) -> None:
        with sess.lock:
            sess.auto_step = step
            sess.updated_at = time.time()

    def _wait_job(self, sess: Session, *, timeout_s: float = 3600.0) -> bool:
        """Wait until status leaves running. False on abort/error/timeout."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if sess._abort.is_set():
                with sess.lock:
                    if sess.status != "running":
                        return False
            with sess.lock:
                st = sess.status
                ph = sess.phase
                err = sess.error
            if st == "running":
                time.sleep(0.35)
                continue
            if st in ("error", "aborted") or ph == "error" or err:
                return False
            return True
        with sess.lock:
            sess.status = "error"
            sess.phase = "error"
            sess.error = "auto pipeline timed out"
            sess.updated_at = time.time()
        return False

    def _ensure_champion_pool(self, sess: Session) -> list[str]:
        with sess.lock:
            pool = list(sess.pool)
            if pool:
                return pool
            scores = {k: list(v) for k, v in sess.pre_scores.items()}
            pass_mean = sess.pass_mean
            target = max(1, sess.qualify_target)
        summaries = self._summaries_locked(sess, scores, pass_mean)
        # Prefer passed; else top by mean.
        passed = [s["variant_id"] for s in summaries if s.get("passed")]
        if passed:
            pool = passed[:target]
        else:
            pool = [s["variant_id"] for s in summaries if s.get("mean") is not None][:target]
        if not pool:
            raise ValueError("prefilter produced no scored variants for champion pool")
        self.set_pool(sess.id, pool)
        return pool

    def _summaries_locked(
        self, sess: Session, scores_by: dict[str, list[float]], pass_mean: float
    ) -> list[dict]:
        """Summaries helper that does not re-enter sess.lock (caller holds or not)."""
        out = []
        bank = sess.bank
        for vid, scores in scores_by.items():
            st = calc_stats(scores)
            passed = st["mean"] is not None and st["mean"] >= pass_mean
            title = vid
            if bank:
                for v in bank.get("variants") or []:
                    if v["id"] == vid:
                        title = v.get("title") or vid
                        break
            out.append(
                {
                    "variant_id": vid,
                    "title": title,
                    **st,
                    "passed": passed,
                    "composite": round(st["mean"] - 1.5 * (st["sdv"] or 0), 2)
                    if st["mean"] is not None
                    else None,
                }
            )
        out.sort(key=lambda x: (-(x["mean"] or 0), x.get("sdv") or 99))
        return out

    def _extract_best_genome(self, sess: Session, champion_mark: str) -> dict[str, Any]:
        with sess.lock:
            marks = dict(sess.marks or {})
            bank = dict(sess.bank or {})
            champ_sum = sess._summaries(sess.champ_scores, sess.pass_mean)
            baseline_sum = sess._baseline_summaries()
            case = dict(sess.case or {})
            oral = sess.oral
            model = sess.model
            preferred = champion_mark if champion_mark in ("perf", "stable", "balanced") else "balanced"
            vid = marks.get(preferred) or marks.get("balanced") or marks.get("perf") or marks.get("stable")
            mark = preferred if marks.get(preferred) else (
                "balanced" if marks.get("balanced") else ("perf" if marks.get("perf") else "stable")
            )
        if not vid:
            raise ValueError("no champion marks — finals empty?")
        variant = None
        for v in bank.get("variants") or []:
            if v.get("id") == vid:
                variant = v
                break
        if not variant:
            raise ValueError(f"champion variant missing in bank: {vid}")
        slots = dict(variant.get("slots") or {})
        alleles = bank.get("alleles") or {}
        slot_texts: dict[str, Any] = {}
        for slot, allele_id in slots.items():
            texts = []
            for a in alleles.get(slot) or []:
                if a.get("id") == allele_id:
                    texts.append(
                        {
                            "id": a.get("id"),
                            "label": a.get("label"),
                            "text": a.get("text"),
                        }
                    )
                    break
            slot_texts[slot] = {
                "allele_id": allele_id,
                "allele": texts[0] if texts else None,
            }
        summary = next((s for s in champ_sum if s.get("variant_id") == vid), None)
        out = {
            "version": 1,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": sess.id,
            "oral": oral,
            "model": model,
            "case": {
                "id": case.get("id"),
                "title": case.get("title"),
                "suite": case.get("suite"),
                "level": case.get("level"),
                "dimension": case.get("dimension"),
            },
            "champion_mark": mark,
            "marks": marks,
            "variant_id": vid,
            "title": variant.get("title") or vid,
            "hash": variant.get("hash"),
            "slots": slots,
            "slot_texts": slot_texts,
            "champ_summary": summary,
            "champ_summaries": champ_sum,
            "baseline_summaries": baseline_sum,
            "token_usage": sess.token_meter.summary(),
        }
        if variant.get("skills"):
            out["skills"] = variant.get("skills")
        return out

    def _run_auto(self, sess: Session, api_key: str, skip_baseline: bool, do_save: bool) -> None:
        try:
            if skip_baseline:
                self._set_auto_step(sess, "baseline")
                self.skip_baseline(sess.id)
            else:
                self._set_auto_step(sess, "baseline")
                self.start_baseline(
                    sess.id,
                    api_key=api_key,
                    baseline_reps=sess.baseline_reps,
                    workers=sess.workers,
                    model=sess.model,
                )
                if not self._wait_job(sess):
                    return

            if sess._abort.is_set():
                return

            self._set_auto_step(sess, "genomes")
            self.generate_genomes(sess.id, api_key=api_key, model=sess.model)

            if sess._abort.is_set():
                return

            self._set_auto_step(sess, "prefilter")
            self.start_prefilter(
                sess.id,
                api_key=api_key,
                pre_reps=sess.pre_reps,
                qualify_target=sess.qualify_target,
                pass_mean=sess.pass_mean,
                workers=sess.workers,
            )
            if not self._wait_job(sess):
                return

            if sess._abort.is_set():
                return

            self._ensure_champion_pool(sess)

            self._set_auto_step(sess, "champion")
            self.start_champion(
                sess.id,
                api_key=api_key,
                champ_reps=sess.champ_reps,
                workers=sess.workers,
            )
            if not self._wait_job(sess):
                return

            if sess._abort.is_set():
                return

            mark = sess.champion_mark
            best = self._extract_best_genome(sess, mark)
            with sess.lock:
                sess.best_genome = best
                sess.updated_at = time.time()

            save_info: dict[str, Any] = {}
            if do_save:
                self._set_auto_step(sess, "save")
                import json

                SAVE.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
                best_path = SAVE / f"{stamp}_best_genome_{sess.id}_v1.0.json"
                best_path.write_text(
                    json.dumps(best, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                saved = self.save_session(
                    sess.id, freeze_demo=False, label="auto", version_tag="v1.0"
                )
                save_info = {
                    "best_genome_path": str(best_path.relative_to(ROOT)),
                    "pack_path": saved.get("pack_path"),
                    "log_path": saved.get("log_path"),
                }

            with sess.lock:
                sess.auto_save = save_info or None
                sess.auto_step = "done"
                sess.phase = "done"
                sess.status = "done"
                sess.updated_at = time.time()
            rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
            rlog.record_phase("done", note="auto")
        except Exception as e:  # noqa: BLE001
            with sess.lock:
                sess.status = "error"
                sess.phase = "error"
                sess.auto_step = "error"
                sess.error = f"auto: {e}"
                sess.updated_at = time.time()

    def abort(self, session_id: str) -> Session:
        sess = self._require(session_id)
        sess._abort.set()
        with sess.lock:
            sess.status = "aborted"
            sess.updated_at = time.time()
        return sess

    def _require(self, session_id: str) -> Session:
        sess = self.get(session_id)
        if not sess:
            raise KeyError(session_id)
        return sess

    def _run_one(
        self,
        *,
        api_key: str,
        model: str,
        case: dict,
        bank: dict,
        vid: str,
        rep: int,
        reps: int,
        abort: threading.Event,
        meter: TokenMeter | None = None,
    ) -> dict[str, Any]:
        ctx = meter.activate() if meter is not None else nullcontext()
        with ctx:
            return self._run_one_inner(
                api_key=api_key,
                model=model,
                case=case,
                bank=bank,
                vid=vid,
                rep=rep,
                reps=reps,
                abort=abort,
            )

    def _run_one_inner(
        self,
        *,
        api_key: str,
        model: str,
        case: dict,
        bank: dict,
        vid: str,
        rep: int,
        reps: int,
        abort: threading.Event,
    ) -> dict[str, Any]:
        if abort.is_set():
            return {"aborted": True, "variant_id": vid, "rep": rep}
        vmap = variant_map(bank)
        host = host_of(case.get("messages") or [])
        jbody = judge_body(case)
        variant = vmap[vid]
        system = assemble_system(host, bank, variant)
        messages = build_messages(case, system)
        gen = chat_completions(
            api_key, model, messages, max_tokens=2200, reasoning_effort="low", purpose="answer"
        )
        content = extract_content(gen)
        if abort.is_set():
            return {"aborted": True, "variant_id": vid, "rep": rep}
        jr = judge_with_retries(api_key, model, jbody, content, max_attempts=3)
        score = float(jr["score"]) if jr.get("score") is not None else None
        return {
            "variant_id": vid,
            "rep": rep,
            "reps": reps,
            "title": variant.get("title") or vid,
            "hash": variant.get("hash") or vid,
            "score": score,
            "ok": jr.get("ok"),
            "gene_slots": variant.get("slots") or {},
            "preview": (content or "")[:280],
            "chars": len(content or ""),
        }

    def _run_baseline_one(
        self,
        *,
        api_key: str,
        model: str,
        case: dict,
        arm: str,
        title: str,
        rep: int,
        reps: int,
        abort: threading.Event,
        meter: TokenMeter | None = None,
    ) -> dict[str, Any]:
        ctx = meter.activate() if meter is not None else nullcontext()
        with ctx:
            return self._run_baseline_one_inner(
                api_key=api_key,
                model=model,
                case=case,
                arm=arm,
                title=title,
                rep=rep,
                reps=reps,
                abort=abort,
            )

    def _run_baseline_one_inner(
        self,
        *,
        api_key: str,
        model: str,
        case: dict,
        arm: str,
        title: str,
        rep: int,
        reps: int,
        abort: threading.Event,
    ) -> dict[str, Any]:
        if abort.is_set():
            return {"aborted": True, "arm": arm, "rep": rep}
        jbody = judge_body(case)
        messages = build_baseline_messages(case, arm)
        gen = chat_completions(
            api_key, model, messages, max_tokens=2200, reasoning_effort="low", purpose="answer"
        )
        content = extract_content(gen)
        if abort.is_set():
            return {"aborted": True, "arm": arm, "rep": rep}
        jr = judge_with_retries(api_key, model, jbody, content, max_attempts=3)
        score = float(jr["score"]) if jr.get("score") is not None else None
        return {
            "arm": arm,
            "variant_id": arm,
            "rep": rep,
            "reps": reps,
            "title": title,
            "score": score,
            "ok": jr.get("ok"),
            "preview": (content or "")[:280],
            "chars": len(content or ""),
        }

    def _run_baseline(
        self,
        sess: Session,
        api_key: str,
        case: dict,
        reps: int,
        workers: int,
        model: str,
    ) -> None:
        tasks = [(arm["id"], arm["title"], r) for arm in BASELINE_ARMS for r in range(1, reps + 1)]
        try:
            with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as pool_ex:
                futs = {
                    pool_ex.submit(
                        self._run_baseline_one,
                        api_key=api_key,
                        model=model,
                        case=case,
                        arm=arm,
                        title=title,
                        rep=rep,
                        reps=reps,
                        abort=sess._abort,
                        meter=sess.token_meter,
                    ): (arm, rep)
                    for arm, title, rep in tasks
                }
                for fut in as_completed(futs):
                    if sess._abort.is_set():
                        break
                    arm, rep = futs[fut]
                    try:
                        row = fut.result()
                    except Exception as e:  # noqa: BLE001
                        with sess.lock:
                            sess.done += 1
                            sess.logs.insert(
                                0,
                                {
                                    "n": sess.done,
                                    "error": str(e),
                                    "variant_id": arm,
                                    "title": arm,
                                    "rep": rep,
                                    "stage": "baseline",
                                },
                            )
                            sess.updated_at = time.time()
                        continue
                    if row.get("aborted"):
                        continue
                    with sess.lock:
                        sess.done += 1
                        if row.get("score") is not None:
                            sess.baseline_scores.setdefault(arm, []).append(float(row["score"]))
                        st = calc_stats(sess.baseline_scores.get(arm) or [])
                        sess.logs.insert(
                            0,
                            {
                                "n": sess.done,
                                "stage": "baseline",
                                "rep": row["rep"],
                                "reps": reps,
                                "variant_id": arm,
                                "title": row.get("title") or arm,
                                "score": row.get("score"),
                                "mean_so_far": st["mean"],
                                "sdv_so_far": st["sdv"],
                                "preview": row.get("preview"),
                            },
                        )
                        sess.updated_at = time.time()
            with sess.lock:
                if sess._abort.is_set():
                    sess.status = "aborted"
                    if sess.phase == "baselining":
                        sess.phase = "case_ready"
                else:
                    sess.status = "done"
                    sess.phase = "baseline_done"
                    scores = {k: list(v) for k, v in sess.baseline_scores.items()}
                    summaries = sess._baseline_summaries()
                    reps_done = sess.baseline_reps
                sess.updated_at = time.time()
            if not sess._abort.is_set() and sess.phase == "baseline_done":
                rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
                rlog.record_baseline(scores=scores, summaries=summaries, reps=reps_done)
                rlog.record_phase("baseline_done")
        except Exception as e:  # noqa: BLE001
            with sess.lock:
                sess.status = "error"
                sess.phase = "error"
                sess.error = str(e)
                sess.updated_at = time.time()

    def _run_prefilter(
        self,
        sess: Session,
        api_key: str,
        case: dict,
        bank: dict,
        variants: list[str],
        reps: int,
        qualify_target: int,
        pass_mean: float,
        workers: int,
        model: str,
    ) -> None:
        # Genome-batch early stop: finish one genome's reps before starting next when stopping;
        # within a genome, parallelize reps.
        try:
            with sess.lock:
                sess.total = len(variants) * reps
            qualified = 0
            stop_rest = False
            for vid in variants:
                if sess._abort.is_set() or stop_rest:
                    with sess.lock:
                        sess.early_stopped = True
                    break
                # run all reps for this genome
                rows: list[dict] = []
                with ThreadPoolExecutor(max_workers=min(workers, reps)) as pool:
                    futs = [
                        pool.submit(
                            self._run_one,
                            api_key=api_key,
                            model=model,
                            case=case,
                            bank=bank,
                            vid=vid,
                            rep=r,
                            reps=reps,
                            abort=sess._abort,
                            meter=sess.token_meter,
                        )
                        for r in range(1, reps + 1)
                    ]
                    for fut in as_completed(futs):
                        if sess._abort.is_set():
                            break
                        try:
                            row = fut.result()
                        except Exception as e:  # noqa: BLE001
                            with sess.lock:
                                sess.done += 1
                                sess.logs.insert(
                                    0, {"n": sess.done, "error": str(e), "variant_id": vid, "stage": "pre"}
                                )
                                sess.updated_at = time.time()
                            continue
                        if row.get("aborted"):
                            continue
                        rows.append(row)
                        with sess.lock:
                            sess.done += 1
                            if row.get("score") is not None:
                                sess.pre_scores.setdefault(vid, []).append(float(row["score"]))
                            st = calc_stats(sess.pre_scores.get(vid) or [])
                            sess.logs.insert(
                                0,
                                {
                                    "n": sess.done,
                                    "stage": "pre",
                                    "rep": row["rep"],
                                    "reps": reps,
                                    "variant_id": vid,
                                    "title": row.get("title"),
                                    "score": row.get("score"),
                                    "mean_so_far": st["mean"],
                                    "sdv_so_far": st["sdv"],
                                    "preview": row.get("preview"),
                                },
                            )
                            sess.updated_at = time.time()

                with sess.lock:
                    st = calc_stats(sess.pre_scores.get(vid) or [])
                    if st["mean"] is not None and st["mean"] >= pass_mean:
                        qualified += 1
                        sess.qualified_count = qualified
                        if vid not in sess.pool:
                            sess.pool.append(vid)

                if qualified >= qualify_target:
                    stop_rest = True
                    with sess.lock:
                        sess.early_stopped = True
                        # remaining genomes not started — shrink reported total
                        tested = len(sess.pre_scores)
                        sess.total = tested * reps

            with sess.lock:
                if sess._abort.is_set():
                    sess.status = "aborted"
                else:
                    sess.status = "done"
                    sess.phase = "prefilter_done"
                    scores = {k: list(v) for k, v in sess.pre_scores.items()}
                    summaries = sess._summaries(sess.pre_scores, sess.pass_mean)
                    pool = list(sess.pool)
                    payload = {
                        "scores": scores,
                        "summaries": summaries,
                        "pool": pool,
                        "pass_mean": sess.pass_mean,
                        "qualify_target": sess.qualify_target,
                        "qualified_count": sess.qualified_count,
                        "early_stopped": sess.early_stopped,
                        "reps": sess.pre_reps,
                    }
                sess.updated_at = time.time()
            if not sess._abort.is_set() and sess.phase == "prefilter_done":
                rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
                rlog.record_prefilter(**payload)
                rlog.record_phase("prefilter_done")
        except Exception as e:  # noqa: BLE001
            with sess.lock:
                sess.status = "error"
                sess.phase = "error"
                sess.error = str(e)
                sess.updated_at = time.time()

    def _run_champion(
        self,
        sess: Session,
        api_key: str,
        case: dict,
        bank: dict,
        pool: list[str],
        reps: int,
        workers: int,
        model: str,
    ) -> None:
        tasks = [(vid, r) for vid in pool for r in range(1, reps + 1)]
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool_ex:
                futs = {
                    pool_ex.submit(
                        self._run_one,
                        api_key=api_key,
                        model=model,
                        case=case,
                        bank=bank,
                        vid=vid,
                        rep=rep,
                        reps=reps,
                        abort=sess._abort,
                        meter=sess.token_meter,
                    ): (vid, rep)
                    for vid, rep in tasks
                }
                for fut in as_completed(futs):
                    if sess._abort.is_set():
                        break
                    vid, rep = futs[fut]
                    try:
                        row = fut.result()
                    except Exception as e:  # noqa: BLE001
                        with sess.lock:
                            sess.done += 1
                            sess.logs.insert(
                                0,
                                {
                                    "n": sess.done,
                                    "error": str(e),
                                    "variant_id": vid,
                                    "rep": rep,
                                    "stage": "champ",
                                },
                            )
                            sess.updated_at = time.time()
                        continue
                    if row.get("aborted"):
                        continue
                    with sess.lock:
                        sess.done += 1
                        if row.get("score") is not None:
                            sess.champ_scores.setdefault(vid, []).append(float(row["score"]))
                        st = calc_stats(sess.champ_scores.get(vid) or [])
                        sess.logs.insert(
                            0,
                            {
                                "n": sess.done,
                                "stage": "champ",
                                "rep": row["rep"],
                                "reps": reps,
                                "variant_id": vid,
                                "title": row.get("title"),
                                "score": row.get("score"),
                                "mean_so_far": st["mean"],
                                "sdv_so_far": st["sdv"],
                                "preview": row.get("preview"),
                            },
                        )
                        sess.updated_at = time.time()
            with sess.lock:
                if sess._abort.is_set():
                    sess.status = "aborted"
                else:
                    summaries = sess._summaries(sess.champ_scores, sess.pass_mean)
                    sess.marks = pick_marks(summaries)
                    sess.status = "done"
                    sess.phase = "done"
                    champ_payload = {
                        "scores": {k: list(v) for k, v in sess.champ_scores.items()},
                        "summaries": summaries,
                        "pool": list(sess.pool),
                        "marks": dict(sess.marks),
                        "reps": sess.champ_reps,
                    }
                sess.updated_at = time.time()
            if not sess._abort.is_set() and sess.phase == "done":
                rlog = get_or_create_log(sess.id, model=sess.model, oral=sess.oral)
                rlog.record_champion(**champ_payload)
                rlog.record_phase("done")
        except Exception as e:  # noqa: BLE001
            with sess.lock:
                sess.status = "error"
                sess.phase = "error"
                sess.error = str(e)
                sess.updated_at = time.time()


# Back-compat aliases used by old live routes (optional thin wrapper)
MANAGER = SessionManager()
