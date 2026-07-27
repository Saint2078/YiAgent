#!/usr/bin/env python3
"""Live-capture critical-thinking demo: A/B baseline (+ optional pre/champ) → demo_pack.json + save/."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
SAVE = ROOT / "save"
BASE = "http://127.0.0.1:8787"


def http(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} → {e.code}: {err}") from e


def poll(session_id: str, want_phases: set[str], timeout_s: int = 1800) -> dict:
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout_s:
        last = http("GET", f"/api/session/{session_id}")
        st = last.get("status")
        ph = last.get("phase")
        print(
            f"  … status={st} phase={ph} done={last.get('done')}/{last.get('total')}",
            flush=True,
        )
        if st == "error":
            raise RuntimeError(last.get("error") or "session error")
        if st == "aborted":
            raise RuntimeError("aborted")
        if ph in want_phases and st != "running":
            return last
        time.sleep(3)
    raise TimeoutError(f"timeout waiting for {want_phases}; last={last.get('phase')}")


def main() -> int:
    key_file = Path("/tmp/yiagent_demo_key.env")
    if not key_file.is_file():
        print("missing /tmp/yiagent_demo_key.env", file=sys.stderr)
        return 2
    api_key = key_file.read_text().strip()
    model = "k3"
    workers = 6
    baseline_reps = 5
    pre_reps = 3
    champ_reps = 5

    print("== health", http("GET", "/api/health"), flush=True)
    print("== start demo/live A/B", flush=True)
    snap = http(
        "POST",
        "/api/session/demo/live",
        {
            "api_key": api_key,
            "model": model,
            "baseline_reps": baseline_reps,
            "workers": workers,
        },
    )
    sid = snap["id"]
    print("session", sid, flush=True)
    snap = poll(sid, {"baseline_done"})
    print("baseline_summaries", snap.get("baseline_summaries"), flush=True)

    print("== attach fixture bank", flush=True)
    snap = http("POST", f"/api/session/{sid}/bank/fixture", {})
    print("variants", len(snap.get("variants") or []), "phase", snap.get("phase"), flush=True)

    print("== prefilter", flush=True)
    http(
        "POST",
        f"/api/session/{sid}/prefilter/start",
        {
            "api_key": api_key,
            "pre_reps": pre_reps,
            "qualify_target": 3,
            "pass_mean": 70,
            "workers": workers,
        },
    )
    snap = poll(sid, {"prefilter_done"})
    print(
        "pre n=",
        len(snap.get("pre_summaries") or []),
        "pool",
        snap.get("pool"),
        flush=True,
    )

    pool = list(snap.get("pool") or [])
    if not pool:
        # take top 3 by mean
        rows = sorted(
            snap.get("pre_summaries") or [],
            key=lambda r: -(r.get("mean") or 0),
        )
        pool = [r["variant_id"] for r in rows[:3]]
    if pool:
        http("POST", f"/api/session/{sid}/champion/pool", {"variant_ids": pool})
        print("== champion", pool, flush=True)
        http(
            "POST",
            f"/api/session/{sid}/champion/start",
            {"api_key": api_key, "champ_reps": champ_reps, "workers": workers},
        )
        snap = poll(sid, {"done"})
        print("marks", snap.get("marks"), flush=True)

    pack = http("GET", f"/api/session/{sid}/export")
    # Prefer a browsable frozen phase
    if pack.get("phase") == "done":
        pass
    elif pack.get("pre_scores"):
        pack["phase"] = "prefilter_done"
    elif pack.get("bank"):
        pack["phase"] = "genomes_ready"
    else:
        pack["phase"] = "baseline_done"

    SAVE.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    save_path = SAVE / f"{ts}_demo_capture_criticalthinking_v1.0.json"
    pack_path = FIX / "demo_pack.json"
    save_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", save_path, flush=True)
    print("wrote", pack_path, flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
