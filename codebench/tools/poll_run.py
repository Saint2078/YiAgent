#!/usr/bin/env python3
"""Poll a codebench run until done."""
from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8791"


def main() -> int:
    rid = sys.argv[1] if len(sys.argv) > 1 else ""
    if not rid:
        print("usage: poll_run.py <run_id>", file=sys.stderr)
        return 2
    for i in range(180):
        raw = urllib.request.urlopen(f"{BASE}/api/run/{rid}", timeout=30).read().decode()
        d = json.loads(raw)
        st = d.get("status")
        p = d.get("progress") or {}
        pa = d.get("pass_at_1")
        err = d.get("error")
        print(f"[{i}] status={st} progress={p} pass@1={pa} err={err}", flush=True)
        if st in ("done", "failed", "error"):
            keys = (
                "run_id",
                "status",
                "pass_at_1",
                "by_difficulty",
                "finished_at",
                "error",
                "progress",
            )
            print(json.dumps({k: d.get(k) for k in keys}, ensure_ascii=False, indent=2))
            return 0 if st == "done" else 1
        time.sleep(30)
    print("still running after poll window")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
