"""用 LiveCodeBench 官方 testing 路径判一道题。"""
from __future__ import annotations

import json
import os
import sys
from typing import Any


def _ensure_lcb() -> None:
    root = os.environ.get("CB_LCB_ROOT", "/lcb")
    if root not in sys.path:
        sys.path.insert(0, root)


def grade_one(problem: dict[str, Any], code: str, *, timeout: int = 6) -> dict[str, Any]:
    _ensure_lcb()
    from lcb_runner.evaluation.compute_code_generation_metrics import check_correctness

    sample = {"input_output": json.dumps(problem["input_output"])}
    if not code.strip():
        return {"passed": False, "detail": "empty_code", "results": []}
    results, meta = check_correctness(sample, code, timeout=timeout, debug=False)
    # results: list of True/False/-1 per test
    oks = [bool(x is True or x == 1) for x in results]
    passed = bool(oks) and all(oks)
    return {
        "passed": passed,
        "n_tests": len(oks),
        "n_ok": sum(1 for x in oks if x),
        "results": results,
        "meta": meta if isinstance(meta, dict) else {"meta": str(meta)},
    }
