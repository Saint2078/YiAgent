"""Session-based factory pipeline: case → genomes → prefilter → champion."""

from __future__ import annotations

import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from assemble import assemble_system, build_messages, host_of, judge_body, variant_map
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
from kimi_client import chat_completions, extract_content

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"


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
    # idle|case_ready|genomes_ready|prefiltering|prefilter_done|championing|done|error
    oral: str = ""
    case: dict | None = None
    bank: dict | None = None
    target_text: str = ""
    criteria_text: str = ""
    pass_mean: float = 70.0
    qualify_target: int = 3
    pre_reps: int = 3
    champ_reps: int = 5
    workers: int = 4
    pre_scores: dict[str, list[float]] = field(default_factory=dict)
    champ_scores: dict[str, list[float]] = field(default_factory=dict)
    pool: list[str] = field(default_factory=list)
    logs: list[dict] = field(default_factory=list)
    status: str = "idle"  # idle|running|done|aborted|error
    total: int = 0
    done: int = 0
    qualified_count: int = 0
    early_stopped: bool = False
    marks: dict[str, str | None] = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)
    _abort: threading.Event = field(default_factory=threading.Event)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            pre_sum = self._summaries(self.pre_scores, self.pass_mean)
            champ_sum = self._summaries(self.champ_scores, self.pass_mean)
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
                "pre_reps": self.pre_reps,
                "champ_reps": self.champ_reps,
                "workers": self.workers,
                "total": self.total,
                "done": self.done,
                "qualified_count": self.qualified_count,
                "early_stopped": self.early_stopped,
                "pre_summaries": pre_sum,
                "champ_summaries": champ_sum,
                "pool": list(self.pool),
                "marks": dict(self.marks),
                "logs": list(self.logs)[:80],
                "error": self.error,
                "updated_at": self.updated_at,
            }

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
        return sess

    def hydrate_demo(self) -> Session:
        case = normalize_case(dict(self.fixture_case), oral="演示：批判思维虚假二选一")
        bank = dict(self.fixture_bank)
        sess = Session(
            id=uuid.uuid4().hex[:12],
            model="demo",
            phase="genomes_ready",
            oral="演示：批判思维虚假二选一",
            case=case,
            bank=bank,
            target_text=format_target_text(case),
            criteria_text=format_criteria_text(case),
            status="idle",
        )
        with self._lock:
            self._sessions[sess.id] = sess
        return sess

    def update_case_texts(
        self, session_id: str, *, target_text: str | None = None, criteria_text: str | None = None
    ) -> Session:
        sess = self._require(session_id)
        with sess.lock:
            if target_text is not None:
                sess.target_text = target_text
                sess.case = parse_target_text(target_text, sess.case)
            if criteria_text is not None:
                sess.criteria_text = criteria_text
                sess.case = parse_criteria_text(criteria_text, sess.case)
            sess.updated_at = time.time()
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
            sess.logs = []
            sess.marks = {}
            sess.qualified_count = 0
            sess.early_stopped = False
            sess.error = None
            sess.status = "idle"
            sess.updated_at = time.time()
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
            sess.logs = []
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
                    # ensure pool = passed by default (already added); keep as-is
                sess.updated_at = time.time()
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
                sess.updated_at = time.time()
        except Exception as e:  # noqa: BLE001
            with sess.lock:
                sess.status = "error"
                sess.phase = "error"
                sess.error = str(e)
                sess.updated_at = time.time()


# Back-compat aliases used by old live routes (optional thin wrapper)
MANAGER = SessionManager()
