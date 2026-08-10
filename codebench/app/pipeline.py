from __future__ import annotations

import json
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import extract, grade_lcb, kimi, sample50
from .config import settings

_lock = threading.Lock()
_runs: dict[str, dict[str, Any]] = {}

DEFAULT_ROLE = "coding_board_racer"
BARE_ROLE = "coding_board_bare"
GRADE_TIMEOUT_S = 12  # private 用例更多，略放宽


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def os_role_dir() -> str:
    import os

    return os.environ.get("CB_ROLES_DIR", "/srv/roles")


def role_file(role_id: str) -> Path:
    return Path(os_role_dir()) / f"{role_id}.json"


def load_role(role_id: str = DEFAULT_ROLE) -> dict[str, Any]:
    p = role_file(role_id)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sample50_path() -> Path:
    """正式 LCB 50 题落盘路径（构建目标；与本地 20 题包分离）。"""
    import os

    pref = os.environ.get("CB_SAMPLE_FILE", "").strip()
    if pref:
        return Path(pref)
    return Path(settings.data_dir) / "sample50_release_v5.json"


def sample_path() -> Path:
    import os

    pref = os.environ.get("CB_SAMPLE_FILE", "").strip()
    if pref:
        return Path(pref)
    lcb = sample50_path()
    if lcb.exists():
        return lcb
    local = Path(settings.data_dir) / "sample_local20.json"
    return local if local.exists() else lcb


def ensure_sample(*, rebuild: bool = False) -> dict[str, Any]:
    """加载抽样；rebuild=True 或 tag 不是 r2 时重建。"""
    p = sample50_path()
    if p.exists() and not rebuild:
        data = sample50.load_sample(p)
        meta = data.get("meta") or {}
        if meta.get("tests") == "public_and_private" and meta.get("sample_tag") == sample50.SAMPLE_TAG:
            return data
        # 旧包：自动升级为 r2
        rebuild = True
    if rebuild or not p.exists():
        sample50.build_sample(p)
    return sample50.load_sample(p)


def get_run(run_id: str) -> dict[str, Any] | None:
    with _lock:
        return _runs.get(run_id)


def list_runs() -> list[dict[str, Any]]:
    with _lock:
        rows = []
        for r in _runs.values():
            rows.append(
                {
                    "run_id": r["run_id"],
                    "status": r["status"],
                    "role_id": r.get("role_id"),
                    "mode": r.get("mode"),
                    "progress": r.get("progress"),
                    "pass_at_1": r.get("pass_at_1"),
                    "started_at": r.get("started_at"),
                    "finished_at": r.get("finished_at"),
                }
            )
        return sorted(rows, key=lambda x: x.get("started_at") or "", reverse=True)


def start_run(*, limit: int | None = None, role_id: str = DEFAULT_ROLE, rebuild_sample: bool = False) -> str:
    role = load_role(role_id)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run = {
        "run_id": run_id,
        "status": "starting",
        "mode": "bare" if role_id == BARE_ROLE else "genome",
        "role_id": role.get("role_id"),
        "role_title": role.get("title"),
        "goal_id": role.get("goal_id"),
        "started_at": _now(),
        "finished_at": None,
        "progress": {"done": 0, "total": 0},
        "pass_at_1": None,
        "by_difficulty": {},
        "error": None,
        "limit": limit,
        "rebuild_sample": rebuild_sample,
        "results": [],
    }
    with _lock:
        _runs[run_id] = run
    t = threading.Thread(target=_worker, args=(run_id, role_id), daemon=True)
    t.start()
    return run_id


def start_compare(*, limit: int | None = None, rebuild_sample: bool = True) -> str:
    """顺序跑基因组 + 裸跑，写入 latest_compare.json。"""
    cmp_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-cmp-" + uuid.uuid4().hex[:4]
    run = {
        "run_id": cmp_id,
        "status": "starting",
        "mode": "compare",
        "role_id": "compare_genome_vs_bare",
        "role_title": "基因组 vs 裸跑",
        "goal_id": "GOAL-CODEBENCH-B-001",
        "started_at": _now(),
        "finished_at": None,
        "progress": {"done": 0, "total": 0},
        "pass_at_1": None,
        "by_difficulty": {},
        "error": None,
        "limit": limit,
        "rebuild_sample": rebuild_sample,
        "results": [],
        "arms": {},
    }
    with _lock:
        _runs[cmp_id] = run
    t = threading.Thread(target=_compare_worker, args=(cmp_id,), daemon=True)
    t.start()
    return cmp_id


def _compare_worker(cmp_id: str) -> None:
    run = _runs[cmp_id]
    try:
        run["status"] = "sampling"
        data = ensure_sample(rebuild=bool(run.get("rebuild_sample")))
        problems = list(data["problems"])
        lim = run.get("limit")
        if lim:
            problems = problems[: int(lim)]
        run["sample_meta"] = data.get("meta")
        total_steps = len(problems) * 2
        run["progress"] = {"done": 0, "total": total_steps}
        run["status"] = "running"

        arms: dict[str, Any] = {}
        done = 0
        for role_id, key in ((DEFAULT_ROLE, "genome"), (BARE_ROLE, "bare")):
            role = load_role(role_id)
            arm_run = {
                "run_id": f"{cmp_id}-{key}",
                "status": "running",
                "mode": key,
                "role_id": role.get("role_id"),
                "role_title": role.get("title"),
                "goal_id": role.get("goal_id"),
                "started_at": _now(),
                "sample_meta": data.get("meta"),
                "progress": {"done": 0, "total": len(problems)},
                "results": [],
            }
            results, tokens = _solve_problems(
                problems,
                role,
                on_progress=lambda i, rows, _role=role, _arm=arm_run, _done0=done: _arm_progress(
                    run, _arm, _role, i, rows, _done0, total_steps
                ),
            )
            arm_run["results"] = results
            _finalize_stats(arm_run, results, tokens)
            arm_run["status"] = "done"
            arm_run["finished_at"] = _now()
            _write_report(arm_run, role, tokens, latest=False)
            arms[key] = {
                "run_id": arm_run["run_id"],
                "role_id": role.get("role_id"),
                "title": role.get("title"),
                "pass_at_1": arm_run["pass_at_1"],
                "n_pass": arm_run["n_pass"],
                "n_total": arm_run["n_total"],
                "by_difficulty": arm_run["by_difficulty"],
                "tokens": tokens,
                "results": results,
            }
            done += len(problems)
            run["progress"] = {"done": done, "total": total_steps}
            run["arms"] = {k: {kk: vv for kk, vv in v.items() if kk != "results"} for k, v in arms.items()}

        compare = _build_compare(cmp_id, data.get("meta"), arms)
        run["compare"] = {k: v for k, v in compare.items() if k != "per_problem"}
        run["pass_at_1"] = compare.get("delta_pass_at_1")
        run["results"] = compare.get("per_problem") or []
        run["status"] = "done"
        run["finished_at"] = _now()
        _write_compare(compare)
        # 指针：latest 用基因组臂，便于旧 UI；compare 另存
        if "genome" in arms:
            g = load_role(DEFAULT_ROLE)
            g_run = {
                "run_id": arms["genome"]["run_id"],
                "goal_id": "GOAL-CODEBENCH-B-001",
                "status": "done",
                "mode": "genome",
                "role_id": g.get("role_id"),
                "sample_meta": data.get("meta"),
                "pass_at_1": arms["genome"]["pass_at_1"],
                "n_pass": arms["genome"]["n_pass"],
                "n_total": arms["genome"]["n_total"],
                "by_difficulty": arms["genome"]["by_difficulty"],
                "started_at": run.get("started_at"),
                "finished_at": run.get("finished_at"),
                "progress": {"done": len(problems), "total": len(problems)},
                "results": arms["genome"]["results"],
            }
            _write_report(g_run, g, arms["genome"].get("tokens") or 0, latest=True)
    except Exception as e:
        run["status"] = "error"
        run["error"] = str(e)
        run["traceback"] = traceback.format_exc()[-4000:]
        run["finished_at"] = _now()


def _arm_progress(
    cmp_run: dict,
    arm_run: dict,
    role: dict,
    i: int,
    rows: list,
    done0: int,
    total_steps: int,
) -> None:
    arm_run["results"] = rows
    arm_run["progress"] = {"done": i + 1, "total": arm_run["progress"]["total"]}
    cmp_run["progress"] = {"done": done0 + i + 1, "total": total_steps}
    cmp_run["arms"] = cmp_run.get("arms") or {}
    cmp_run["arms"][arm_run["mode"]] = {
        "run_id": arm_run["run_id"],
        "role_id": role.get("role_id"),
        "progress": arm_run["progress"],
        "status": "running",
    }
    _write_report(arm_run, role, 0, latest=False)


def _worker(run_id: str, role_id: str) -> None:
    run = _runs[run_id]
    try:
        role = load_role(role_id)
        run["status"] = "sampling"
        data = ensure_sample(rebuild=bool(run.get("rebuild_sample")))
        problems = data["problems"]
        lim = run.get("limit")
        if lim:
            problems = problems[: int(lim)]
        run["sample_meta"] = data.get("meta")
        run["progress"] = {"done": 0, "total": len(problems)}
        run["status"] = "running"

        def on_progress(i: int, rows: list) -> None:
            run["results"] = rows
            run["progress"] = {"done": i + 1, "total": len(problems)}
            _write_report(run, role, 0, latest=True)

        results, tokens = _solve_problems(problems, role, on_progress=on_progress)
        run["results"] = results
        _finalize_stats(run, results, tokens)
        run["status"] = "done"
        run["finished_at"] = _now()
        _write_report(run, role, tokens, latest=True)
    except Exception as e:
        run["status"] = "error"
        run["error"] = str(e)
        run["traceback"] = traceback.format_exc()[-4000:]
        run["finished_at"] = _now()


def _solve_problems(
    problems: list[dict[str, Any]],
    role: dict[str, Any],
    *,
    on_progress,
) -> tuple[list[dict[str, Any]], int]:
    system = role.get("system_prompt") or ""
    suffix = role.get("user_suffix") or ""
    results: list[dict[str, Any]] = []
    tokens = 0
    for i, prob in enumerate(problems):
        user = _user_prompt(prob) + suffix
        messages = [{"role": "user", "content": user}]
        if system.strip():
            messages = [{"role": "system", "content": system}] + messages
        try:
            resp = kimi.chat(messages, model=role.get("model") or None)
            raw = resp["content"]
            code = extract.extract_python(raw)
            usage = resp.get("usage") or {}
            tokens += int(usage.get("total_tokens") or 0)
        except Exception as e:
            raw, code = "", ""
            grade = {"passed": False, "detail": f"llm_error:{e}", "n_tests": 0, "n_ok": 0}
            results.append(_row(prob, raw, code, grade))
            on_progress(i, results)
            continue
        try:
            grade = grade_lcb.grade_one(prob, code, timeout=GRADE_TIMEOUT_S)
        except Exception as e:
            grade = {
                "passed": False,
                "detail": f"grade_error:{e}",
                "n_tests": 0,
                "n_ok": 0,
                "traceback": traceback.format_exc()[-2000:],
            }
        results.append(_row(prob, raw, code, grade))
        on_progress(i, results)
    return results, tokens


def _finalize_stats(run: dict[str, Any], results: list[dict[str, Any]], tokens: int) -> None:
    n = len(results) or 1
    n_pass = sum(1 for r in results if r.get("passed"))
    run["pass_at_1"] = round(100.0 * n_pass / n, 2)
    run["n_pass"] = n_pass
    run["n_total"] = len(results)
    run["tokens"] = tokens
    by: dict[str, dict[str, int]] = {}
    for r in results:
        d = r.get("difficulty") or "?"
        by.setdefault(d, {"pass": 0, "total": 0})
        by[d]["total"] += 1
        if r.get("passed"):
            by[d]["pass"] += 1
    run["by_difficulty"] = by


def _build_compare(cmp_id: str, sample_meta: Any, arms: dict[str, Any]) -> dict[str, Any]:
    g = arms.get("genome") or {}
    b = arms.get("bare") or {}
    g_map = {r["question_id"]: r for r in (g.get("results") or [])}
    b_map = {r["question_id"]: r for r in (b.get("results") or [])}
    ids = list(g_map.keys()) or list(b_map.keys())
    per = []
    for qid in ids:
        gr = g_map.get(qid) or {}
        br = b_map.get(qid) or {}
        per.append(
            {
                "question_id": qid,
                "question_title": gr.get("question_title") or br.get("question_title"),
                "difficulty": gr.get("difficulty") or br.get("difficulty"),
                "genome_passed": bool(gr.get("passed")),
                "bare_passed": bool(br.get("passed")),
                "n_tests": gr.get("n_tests") or br.get("n_tests"),
                "genome_detail": gr.get("detail"),
                "bare_detail": br.get("detail"),
            }
        )
    gp = g.get("pass_at_1")
    bp = b.get("pass_at_1")
    delta = None
    if gp is not None and bp is not None:
        delta = round(float(gp) - float(bp), 2)
    return {
        "compare_id": cmp_id,
        "goal_id": "GOAL-CODEBENCH-B-001",
        "sample_meta": sample_meta,
        "genome": {
            "run_id": g.get("run_id"),
            "role_id": g.get("role_id"),
            "title": g.get("title"),
            "pass_at_1": gp,
            "n_pass": g.get("n_pass"),
            "n_total": g.get("n_total"),
            "by_difficulty": g.get("by_difficulty"),
            "tokens": g.get("tokens"),
        },
        "bare": {
            "run_id": b.get("run_id"),
            "role_id": b.get("role_id"),
            "title": b.get("title"),
            "pass_at_1": bp,
            "n_pass": b.get("n_pass"),
            "n_total": b.get("n_total"),
            "by_difficulty": b.get("by_difficulty"),
            "tokens": b.get("tokens"),
        },
        "delta_pass_at_1": delta,
        "per_problem": per,
        "finished_at": _now(),
    }


def _user_prompt(prob: dict[str, Any]) -> str:
    q = f"### Question:\n{prob['question_content']}\n\n"
    if prob.get("starter_code"):
        q += (
            "### Format: You will use the following starter code to write the solution "
            "to the problem and enclose your code within delimiters.\n"
        )
        q += f"```python\n{prob['starter_code']}\n```\n\n"
    else:
        q += (
            "### Format: Read the inputs from stdin solve the problem and write the answer "
            "to stdout (do not directly test on the sample inputs). Enclose your code within "
            "delimiters as follows.\n"
        )
        q += "```python\n# YOUR CODE HERE\n```\n\n"
    q += "### Answer: (use the provided format with backticks)\n\n"
    return q


def _row(prob: dict[str, Any], raw: str, code: str, grade: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": prob["question_id"],
        "question_title": prob.get("question_title"),
        "difficulty": prob.get("difficulty"),
        "platform": prob.get("platform"),
        "passed": bool(grade.get("passed")),
        "n_ok": grade.get("n_ok"),
        "n_tests": grade.get("n_tests"),
        "n_public_tests": prob.get("n_public_tests"),
        "n_private_tests": prob.get("n_private_tests"),
        "detail": grade.get("detail"),
        "code_len": len(code or ""),
        "raw_len": len(raw or ""),
        "code_preview": (code or "")[:400],
    }


def _write_report(run: dict[str, Any], role: dict[str, Any], tokens: int, *, latest: bool) -> None:
    out = Path(settings.data_dir) / "runs" / run["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run["run_id"],
        "goal_id": run.get("goal_id"),
        "mode": run.get("mode"),
        "role": {
            "role_id": role.get("role_id"),
            "title": role.get("title"),
            "genome": role.get("genome"),
            "model": role.get("model"),
        },
        "sample_meta": run.get("sample_meta"),
        "status": run["status"],
        "pass_at_1": run.get("pass_at_1"),
        "n_pass": run.get("n_pass"),
        "n_total": run.get("n_total") or run.get("progress", {}).get("done"),
        "by_difficulty": run.get("by_difficulty"),
        "tokens": tokens or run.get("tokens"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "progress": run.get("progress"),
        "results": run.get("results"),
        "error": run.get("error"),
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if latest:
        latest_p = Path(settings.data_dir) / "latest_report.json"
        latest_p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_compare(compare: dict[str, Any]) -> None:
    out = Path(settings.data_dir) / "runs" / compare["compare_id"]
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(compare, ensure_ascii=False, indent=2)
    (out / "compare.json").write_text(text, encoding="utf-8")
    (Path(settings.data_dir) / "latest_compare.json").write_text(text, encoding="utf-8")
