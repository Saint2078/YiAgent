"""Factory run log: case / judge / A·B·C results.

Local JSONL + session snapshot under save/logs/.
Remote ship is stubbed — do not send until explicitly enabled.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "save"
LOG_DIR = SAVE / "logs"

# Future: point at your ingest endpoint. Keep empty / False for now.
SHIP_ENABLED = False
SHIP_URL: str | None = None  # e.g. "https://your-server.example/ingest/yiagent-run"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunLog:
    """One session's structured experiment log (题目 / 裁判 / A·B·C / 测试结果)."""

    def __init__(self, session_id: str, *, model: str = "", oral: str = "") -> None:
        self.id = uuid.uuid4().hex[:12]
        self.session_id = session_id
        self.version = "0.1"
        self.created_at = _now_iso()
        self.model = model
        self.oral = oral
        self.events: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._ship_pending: list[Path] = []

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        row = {
            "ts": _now_iso(),
            "kind": kind,
            "session_id": self.session_id,
            "payload": payload,
        }
        with self._lock:
            self.events.append(row)

    def record_case(
        self,
        *,
        oral: str,
        case: dict | None,
        target_text: str,
        criteria_text: str,
        judge: dict | None,
    ) -> None:
        self.oral = oral or self.oral
        self._emit(
            "case",
            {
                "oral": oral,
                "case": case,
                "target_text": target_text,
                "criteria_text": criteria_text,
                "judge": judge,
            },
        )

    def record_baseline(
        self,
        *,
        scores: dict[str, list[float]],
        summaries: list[dict],
        reps: int,
        skipped: bool = False,
    ) -> None:
        """A / B floor–ceiling baseline."""
        self._emit(
            "baseline_ab",
            {
                "arms": ["A", "B"],
                "reps": reps,
                "skipped": skipped,
                "scores": {k: list(v) for k, v in scores.items()},
                "summaries": summaries,
            },
        )

    def record_genomes(self, *, bank: dict | None) -> None:
        """Candidate genomes (pipeline C relative to A/B)."""
        variants = []
        if bank:
            for v in bank.get("variants") or []:
                variants.append(
                    {
                        "id": v.get("id"),
                        "title": v.get("title"),
                        "slots": v.get("slots") or {},
                        "hash": v.get("hash"),
                    }
                )
        self._emit(
            "genomes_c",
            {
                "variant_count": len(variants),
                "variants": variants,
                "allele_slot_keys": list((bank or {}).get("alleles") or {}.keys()),
            },
        )

    def record_prefilter(
        self,
        *,
        scores: dict[str, list[float]],
        summaries: list[dict],
        pool: list[str],
        pass_mean: float,
        qualify_target: int,
        qualified_count: int,
        early_stopped: bool,
        reps: int,
    ) -> None:
        self._emit(
            "prefilter",
            {
                "reps": reps,
                "pass_mean": pass_mean,
                "qualify_target": qualify_target,
                "qualified_count": qualified_count,
                "early_stopped": early_stopped,
                "scores": {k: list(v) for k, v in scores.items()},
                "summaries": summaries,
                "pool": list(pool),
            },
        )

    def record_champion(
        self,
        *,
        scores: dict[str, list[float]],
        summaries: list[dict],
        pool: list[str],
        marks: dict[str, str | None],
        reps: int,
    ) -> None:
        self._emit(
            "champion",
            {
                "reps": reps,
                "pool": list(pool),
                "marks": dict(marks),
                "scores": {k: list(v) for k, v in scores.items()},
                "summaries": summaries,
            },
        )

    def record_phase(self, phase: str, *, note: str | None = None) -> None:
        self._emit("phase", {"phase": phase, "note": note})

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            events = list(self.events)
        return {
            "schema": "yiagent.factory.run_log",
            "version": self.version,
            "log_id": self.id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "saved_at": _now_iso(),
            "model": self.model,
            "oral": self.oral,
            "events": events,
            "ship": {
                "enabled": SHIP_ENABLED,
                "url": SHIP_URL,
                "status": "local_only" if not SHIP_ENABLED else "pending",
            },
        }

    def write_local(self, *, label: str = "run", version_tag: str = "v0.1") -> Path:
        """Persist under save/logs/ with timestamp + version. Never overwrite."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = _utc_stamp()
        path = LOG_DIR / f"{stamp}_{label}_{self.session_id}_{version_tag}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        # JSONL companion for append-friendly ingest later
        jl = LOG_DIR / f"{stamp}_{label}_{self.session_id}_{version_tag}.jsonl"
        with jl.open("w", encoding="utf-8") as f:
            for ev in self.to_dict()["events"]:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self._ship_pending.append(path)
        return path

    def ship_to_server(self) -> dict[str, Any]:
        """Stub: future HTTP post of run log. No network until SHIP_ENABLED."""
        if not SHIP_ENABLED or not SHIP_URL:
            return {
                "ok": False,
                "skipped": True,
                "reason": "ship not enabled (SHIP_ENABLED=False)",
                "pending_files": [str(p) for p in self._ship_pending],
            }
        # Intentionally not implemented — enable later with real client.
        return {
            "ok": False,
            "skipped": True,
            "reason": "ship client not implemented yet",
            "url": SHIP_URL,
        }


# session_id → RunLog
_REGISTRY: dict[str, RunLog] = {}
_REG_LOCK = threading.Lock()


def get_or_create_log(session_id: str, *, model: str = "", oral: str = "") -> RunLog:
    with _REG_LOCK:
        log = _REGISTRY.get(session_id)
        if log is None:
            log = RunLog(session_id, model=model, oral=oral)
            _REGISTRY[session_id] = log
        else:
            if model:
                log.model = model
            if oral:
                log.oral = oral
        return log


def drop_log(session_id: str) -> None:
    with _REG_LOCK:
        _REGISTRY.pop(session_id, None)
