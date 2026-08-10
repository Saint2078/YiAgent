#!/usr/bin/env python3
"""重跑报告中 llm timeout 的题，并回写 genome/bare/compare。"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# container: /srv/app on PYTHONPATH
sys.path.insert(0, "/srv")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import extract, grade_lcb, kimi, pipeline, sample50  # noqa: E402

DATA = Path(os.environ.get("CB_DATA_DIR", "/data"))
CMP = "20260809-142513-cmp-2b92"
ARMS = {
    "genome": ("coding_board_racer", f"{CMP}-genome"),
    "bare": ("coding_board_bare", f"{CMP}-bare"),
}
KIMI_TIMEOUT = 480.0
GRADE_TIMEOUT = 12
MAX_TRIES = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_timeout(detail: str | None) -> bool:
    d = (detail or "").lower()
    return "timed out" in d or "timeout" in d


def _needs_retry(row: dict) -> bool:
    """首轮 timeout，或本轮冲泡后仍 empty_code（常因 content 空）。"""
    if _is_timeout(row.get("detail")):
        return True
    retry = row.get("retry") or {}
    if retry.get("reason") == "llm_timeout" and (
        row.get("detail") == "empty_code" or not (row.get("code_preview") or "").strip()
    ):
        return True
    return False


def _solve_one(prob: dict, role: dict) -> dict:
    system = role.get("system_prompt") or ""
    suffix = role.get("user_suffix") or ""
    user = pipeline._user_prompt(prob) + suffix
    messages = [{"role": "user", "content": user}]
    if system.strip():
        messages = [{"role": "system", "content": system}] + messages
    last_err = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            print(f"  kimi attempt {attempt}/{MAX_TRIES} timeout={KIMI_TIMEOUT}s…", flush=True)
            resp = kimi.chat(
                messages,
                model=role.get("model") or None,
                timeout=KIMI_TIMEOUT,
                max_tokens=16384,
            )
            raw = resp["content"] or ""
            code = extract.extract_python(raw)
            usage = resp.get("usage") or {}
            tokens = int(usage.get("total_tokens") or 0)
            finish = resp.get("finish_reason")
            print(
                f"  got content_len={len(raw)} code_len={len(code)} tokens={tokens} finish={finish}",
                flush=True,
            )
            if not code.strip():
                # 再试：有时围栏不完整
                if "def " in raw or "class " in raw or "import " in raw:
                    code = raw.strip() + "\n"
            if not code.strip():
                grade = {
                    "passed": False,
                    "detail": "empty_code",
                    "n_tests": 0,
                    "n_ok": 0,
                }
            else:
                grade = grade_lcb.grade_one(prob, code, timeout=GRADE_TIMEOUT)
            row = pipeline._row(prob, raw, code, grade)
            row["retry"] = {
                "at": _now(),
                "attempts": attempt,
                "tokens": tokens,
                "reason": "llm_timeout",
                "finish_reason": finish,
                "raw_preview": raw[:800],
            }
            return row
        except Exception as e:
            last_err = e
            print(f"  attempt failed: {e}", flush=True)
    grade = {
        "passed": False,
        "detail": f"llm_error:{last_err}",
        "n_tests": 0,
        "n_ok": 0,
        "traceback": traceback.format_exc()[-1500:],
    }
    row = pipeline._row(prob, "", "", grade)
    row["retry"] = {"at": _now(), "attempts": MAX_TRIES, "reason": "llm_timeout", "failed": True}
    return row


def _recompute(report: dict) -> None:
    results = report.get("results") or []
    n = len(results) or 1
    n_pass = sum(1 for r in results if r.get("passed"))
    report["pass_at_1"] = round(100.0 * n_pass / n, 2)
    report["n_pass"] = n_pass
    report["n_total"] = len(results)
    by: dict = {}
    for r in results:
        d = r.get("difficulty") or "?"
        by.setdefault(d, {"pass": 0, "total": 0})
        by[d]["total"] += 1
        if r.get("passed"):
            by[d]["pass"] += 1
    report["by_difficulty"] = by
    report["status"] = "done"
    report["retried_timeouts_at"] = _now()


def main() -> int:
    sample = sample50.load_sample(DATA / "sample50_release_v5.json")
    probs = {p["question_id"]: p for p in sample["problems"]}
    updated_arms: dict[str, dict] = {}

    for arm, (role_id, run_id) in ARMS.items():
        path = DATA / "runs" / run_id / "report.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        role = pipeline.load_role(role_id)
        results = report.get("results") or []
        targets = [i for i, r in enumerate(results) if _needs_retry(r)]
        print(f"[{arm}] timeout/retry targets: {len(targets)}", flush=True)
        for i in targets:
            old = results[i]
            qid = old["question_id"]
            prob = probs.get(qid)
            if not prob:
                print(f"  missing problem {qid}", flush=True)
                continue
            print(f"[{arm}] retry {qid} {old.get('question_title')}", flush=True)
            new_row = _solve_one(prob, role)
            print(
                f"  -> passed={new_row.get('passed')} detail={new_row.get('detail')} "
                f"n_ok={new_row.get('n_ok')}/{new_row.get('n_tests')}",
                flush=True,
            )
            results[i] = new_row
        report["results"] = results
        _recompute(report)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        updated_arms[arm] = report
        print(f"[{arm}] pass@1={report['pass_at_1']} ({report['n_pass']}/{report['n_total']})", flush=True)

    # rebuild compare
    g = updated_arms["genome"]
    b = updated_arms["bare"]
    arms = {
        "genome": {
            "run_id": g["run_id"],
            "role_id": (g.get("role") or {}).get("role_id"),
            "title": (g.get("role") or {}).get("title"),
            "pass_at_1": g.get("pass_at_1"),
            "n_pass": g.get("n_pass"),
            "n_total": g.get("n_total"),
            "by_difficulty": g.get("by_difficulty"),
            "tokens": g.get("tokens"),
            "results": g.get("results"),
        },
        "bare": {
            "run_id": b["run_id"],
            "role_id": (b.get("role") or {}).get("role_id"),
            "title": (b.get("role") or {}).get("title"),
            "pass_at_1": b.get("pass_at_1"),
            "n_pass": b.get("n_pass"),
            "n_total": b.get("n_total"),
            "by_difficulty": b.get("by_difficulty"),
            "tokens": b.get("tokens"),
            "results": b.get("results"),
        },
    }
    compare = pipeline._build_compare(CMP, sample.get("meta"), arms)
    compare["retried_timeouts_at"] = _now()
    pipeline._write_compare(compare)
    # refresh latest_report to genome
    (DATA / "latest_report.json").write_text(
        json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "COMPARE",
        "genome",
        compare["genome"]["pass_at_1"],
        "bare",
        compare["bare"]["pass_at_1"],
        "delta",
        compare["delta_pass_at_1"],
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
