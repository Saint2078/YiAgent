"""Session-based factory pipeline: case → baseline A/B → genomes → prefilter → champion."""

from __future__ import annotations

import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    format_criteria_text,
    format_target_text,
    generate_case,
    generate_genomes,
    normalize_case,
    parse_criteria_text,
    parse_target_text,
)
from judge import judge_with_retries
from llm_client import chat_completions, extract_content
from run_log import get_or_create_log

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
                "pre_summaries": pre_sum,
                "champ_summaries": champ_sum,
                "pool": list(self.pool),
                "marks": dict(self.marks),
                "logs": list(self.logs)[:80],
                "error": self.error,
                "frozen_demo": self.frozen_demo,
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
            # Only invalidate A/B when rubric/task text actually changed.
            if changed:
                sess.baseline_scores = {}
                if sess.phase == "baseline_done" and not sess.bank:
                    sess.phase = "case_ready"
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
    ) -> dict[str, Any]:
        if abort.is_set():
            return {"aborted": True, "variant_id": vid, "rep": rep}
        vmap = variant_map(bank)
        host = host_of(case.get("messages") or [])
        jbody = judge_body(case)
        variant = vmap[vid]
        system = assemble_system(host, bank, variant)
        messages = build_messages(case, system)
        gen = chat_completions(api_key, model, messages, max_tokens=2200, reasoning_effort="low")
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
    ) -> dict[str, Any]:
        if abort.is_set():
            return {"aborted": True, "arm": arm, "rep": rep}
        jbody = judge_body(case)
        messages = build_baseline_messages(case, arm)
        gen = chat_completions(api_key, model, messages, max_tokens=2200, reasoning_effort="low")
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
