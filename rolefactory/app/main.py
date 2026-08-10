"""FastAPI 入口。独立容器运行，不依赖 console/factory。"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import anchors as anchors_mod
from . import judge as judge_mod
from . import pipeline
from . import store
from .config import SETTINGS
from .llm import Budget, Session, close_client
from .pipeline import MANAGER, PHASES

app = FastAPI(title="YiAgent RoleFactory", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.allow_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    store.ensure_dirs()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_client()


def _key(body_key: str | None = None) -> str:
    k = (body_key or "").strip() or SETTINGS.api_key()
    if not k:
        raise HTTPException(400, "缺少 API Key：挂载 RF_KEY_FILE 或在请求体传 api_key")
    return k


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "rolefactory",
        "model": SETTINGS.model,
        "base_url": SETTINGS.base_url,
        "key_present": bool(SETTINGS.api_key()),
        "concurrency": SETTINGS.concurrency,
        "cache": SETTINGS.cache_enabled,
        "hedge": {
            "enabled": SETTINGS.hedge_enabled,
            "min_seconds": SETTINGS.hedge_min_seconds,
            "cap_seconds": SETTINGS.hedge_cap_seconds,
            "p50_factor": SETTINGS.hedge_p50_factor,
            "max_rate": SETTINGS.hedge_max_rate,
        },
        "bench_index": SETTINGS.bench_index.is_file(),
        "phases": list(PHASES),
    }


@app.get("/api/bench")
async def bench() -> dict[str, Any]:
    idx = anchors_mod.load_index()
    items = idx.get("benchmarks") or []
    return {
        "count": len(items),
        "runnable_here": sum(1 for e in items if e.get("runnable_here")),
        "pulled": sum(1 for e in items if e.get("pulled")),
        "items": items,
    }


@app.get("/api/anchors")
async def api_anchors(role: str = Query(...), limit: int = Query(5, ge=1, le=20)) -> dict[str, Any]:
    return {"role": role, "anchors": anchors_mod.retrieve(role, limit=limit)}


@app.post("/api/perf/probe")
async def perf_probe(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    """并发压测：n 个独立小请求并行，测服务端可用吞吐与延时分布（绕过缓存）。"""
    n = max(1, min(64, int(payload.get("n") or 8)))
    conc = max(1, min(64, int(payload.get("concurrency") or n)))
    # k3 是推理模型：max_tokens 要含推理开销，给小了会空回复并触发重试风暴，压测数据就不可信
    max_tokens = max(SETTINGS.min_max_tokens, min(4096, int(payload.get("max_tokens") or 1024)))
    session = Session(_key(payload.get("api_key")), payload.get("model"), concurrency=conc, cache=False)
    t0 = time.monotonic()

    async def one(i: int) -> bool:
        try:
            await session.chat(
                [{"role": "user", "content": f"用一句话说明第 {i + 1} 条数据分析常见口径陷阱。"}],
                purpose="probe",
                max_tokens=max_tokens,
                temperature=0.8,
            )
            return True
        except Exception:  # noqa: BLE001
            return False

    got = await asyncio.gather(*(one(i) for i in range(n)))
    wall = max(0.0, time.monotonic() - t0)
    m = session.meter.snapshot()
    return {
        "requests": n,
        "ok": sum(1 for g in got if g),
        "concurrency": conc,
        "wall_seconds": round(wall, 2),
        "throughput_rps": round(sum(1 for g in got if g) / wall, 2) if wall > 0 else None,
        "latency_p50": m.get("latency_p50"),
        "latency_p90": m.get("latency_p90"),
        "latency_p99": m.get("latency_p99"),
        "latency_max": m.get("latency_max"),
        "tokens": m.get("total_tokens"),
        "retries": m.get("retries"),
        "inflight_peak": m.get("inflight_peak"),
        "queue_seconds_sum": m.get("queue_seconds_sum"),
        "api_seconds_sum": m.get("api_seconds_sum"),
        "hedges": m.get("hedges"),
        "hedge_wins": m.get("hedge_wins"),
        # 串行等效秒数 / 墙钟：并发真实收益（排队时间已剔除）
        "speedup_vs_serial": (
            round((m.get("api_seconds_sum") or 0) / wall, 2) if wall > 0 else None
        ),
    }


@app.post("/api/run")
async def start_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    role = str(payload.get("role") or "").strip()
    if not role:
        raise HTTPException(400, "role 必填，例如「数据分析专家」")
    api_key = _key(payload.get("api_key"))
    mode = str(payload.get("scoring_mode") or "objective").strip().lower()
    if mode not in ("objective", "judge"):
        raise HTTPException(400, "scoring_mode 只支持 objective / judge")
    params = {
        "model": (payload.get("model") or SETTINGS.model),
        "scoring_mode": mode,
        "judge_shadow": bool(payload.get("judge_shadow", True)),
        "per_dim": int(payload.get("per_dim") or 2),
        "generations": int(payload.get("generations") or 3),
        "variants_per_gen": int(payload.get("variants_per_gen") or 6),
        "reps": int(payload.get("reps") or 1),
        # holdout 单独提采样：2 个臂 × 5–6 题，多跑几次只多一个批次
        "holdout_reps": int(payload.get("holdout_reps") or 3),
        # 每维留几道给 holdout。默认 1 会把 holdout 题量锁死在维度数（约 6 道），
        # 而那个题量判不出实测效应（PERF.md §10.1）；要判定就往上调，加题比加重复省。
        "holdout_per_dim": int(payload.get("holdout_per_dim") or 1),
        "elite": int(payload.get("elite") or 2),
        "min_gain": float(payload.get("min_gain") or 0.5),
        "patience": int(payload.get("patience") or 1),
        "seed": int(payload.get("seed") or 42),
        "concurrency": int(payload.get("concurrency") or SETTINGS.concurrency),
        "budget_tokens": int(payload.get("budget_tokens") or SETTINGS.default_budget_tokens),
        "budget_seconds": float(payload.get("budget_seconds") or SETTINGS.default_budget_seconds),
        "anchor_limit": int(payload.get("anchor_limit") or 5),
    }
    run = MANAGER.start(role, params, api_key)
    return {"run_id": run.run_id, "status": run.status, "params": params}


@app.get("/api/runs")
async def list_runs(limit: int = Query(30, ge=1, le=200)) -> dict[str, Any]:
    live = [r.snapshot()["run_id"] for r in MANAGER.runs.values()]
    return {"live": live, "items": store.list_runs(limit)}


@app.get("/api/run/{run_id}")
async def get_run(run_id: str, full: bool = Query(False)) -> Any:
    run = MANAGER.get(run_id)
    if run is not None:
        return run.snapshot(full=full)
    disk = store.read_json(store.run_dir(run_id) / "state.json")
    if disk is None:
        raise HTTPException(404, "run 不存在")
    if not full:
        disk.pop("cases", None)
        disk.pop("bank", None)
    return disk


@app.get("/api/run/{run_id}/report")
async def get_report(run_id: str) -> Any:
    rep = store.read_json(store.run_dir(run_id) / "report.json")
    if rep is None:
        raise HTTPException(404, "报告未生成（run 未结束或已失败）")
    return rep


@app.get("/api/run/{run_id}/results")
async def get_results(run_id: str, limit: int = Query(50, ge=1, le=500), full: bool = Query(False)) -> Any:
    path = store.run_dir(run_id) / "results.jsonl"
    if not path.is_file():
        raise HTTPException(404, "无评测明细")
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not full:
                row.pop("reply", None)
            rows.append(row)
    return {"count": len(rows), "items": rows[-limit:]}


@app.get("/api/run/{run_id}/shadow")
async def get_shadow(run_id: str) -> Any:
    """读已存的口径对照结果（由 POST 同路径生成，不再花 token）。"""
    out = store.read_json(store.run_dir(run_id) / "shadow.json")
    if out is None:
        raise HTTPException(404, "未做口径对照（先 POST 同路径）")
    return out


@app.post("/api/run/{run_id}/shadow")
async def shadow_compare(run_id: str, payload: dict[str, Any] = Body(default={})) -> Any:
    """对已存的回答**补跑一遍 LLM 裁判**，与客观分并列对比区分度（不重新作答，不参与选种）。"""
    state = store.read_json(store.run_dir(run_id) / "state.json")
    path = store.run_dir(run_id) / "results.jsonl"
    if not isinstance(state, dict) or not path.is_file():
        raise HTTPException(404, "run 或评测明细不存在")
    cases = {c["id"]: c for c in state.get("cases") or []}
    champ_id = (state.get("champion") or {}).get("id")
    arms = set(payload.get("arms") or [a for a in ("baseline", champ_id) if a])

    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("variant") in arms and r.get("reply") and r.get("case") in cases:
                rows.append(r)
    if not rows:
        raise HTTPException(400, "没有可对照的回答（检查 arms）")
    limit = int(payload.get("limit") or 80)
    rows = rows[:limit]

    session = Session(_key(payload.get("api_key")), payload.get("model"), concurrency=int(payload.get("concurrency") or 16))

    async def one(r: dict[str, Any]) -> None:
        case = cases[r["case"]]
        try:
            res = await judge_mod.judge(session, {**case, "criteria": judge_mod.shadow_criteria(case)}, r["reply"])
            r["judge_score"] = res["total"]
        except Exception as exc:  # noqa: BLE001
            r["judge_error"] = f"{type(exc).__name__}: {exc}"

    await asyncio.gather(*(one(r) for r in rows))

    by_arm: dict[str, dict[str, list[float]]] = {}
    pairs: list[tuple[float, float]] = []
    for r in rows:
        if r.get("judge_score") is None:
            continue
        slot = by_arm.setdefault(r["variant"], {"objective": [], "judge": []})
        slot["objective"].append(float(r["score"]))
        slot["judge"].append(float(r["judge_score"]))
        pairs.append((float(r["score"]), float(r["judge_score"])))

    def mean(v: list[float]) -> float | None:
        return round(sum(v) / len(v), 2) if v else None

    def pearson(ps: list[tuple[float, float]]) -> float | None:
        n = len(ps)
        if n < 3:
            return None
        mx = sum(p[0] for p in ps) / n
        my = sum(p[1] for p in ps) / n
        num = sum((p[0] - mx) * (p[1] - my) for p in ps)
        dx = sum((p[0] - mx) ** 2 for p in ps) ** 0.5
        dy = sum((p[1] - my) ** 2 for p in ps) ** 0.5
        return round(num / (dx * dy), 3) if dx > 0 and dy > 0 else None

    arms_out = {
        k: {
            "n": len(v["judge"]),
            "objective_mean": mean(v["objective"]),
            "judge_mean": mean(v["judge"]),
            "objective_min": round(min(v["objective"]), 2) if v["objective"] else None,
            "objective_max": round(max(v["objective"]), 2) if v["objective"] else None,
            "judge_min": round(min(v["judge"]), 2) if v["judge"] else None,
            "judge_max": round(max(v["judge"]), 2) if v["judge"] else None,
        }
        for k, v in sorted(by_arm.items())
    }
    obj_means = [v["objective_mean"] for v in arms_out.values() if v["objective_mean"] is not None]
    jud_means = [v["judge_mean"] for v in arms_out.values() if v["judge_mean"] is not None]
    out = {
        "run_id": run_id,
        "rows_judged": sum(1 for r in rows if r.get("judge_score") is not None),
        "arms": arms_out,
        "arm_gap_objective": round(max(obj_means) - min(obj_means), 2) if len(obj_means) > 1 else None,
        "arm_gap_judge": round(max(jud_means) - min(jud_means), 2) if len(jud_means) > 1 else None,
        "row_correlation": pearson(pairs),
        "judge_high_objective_low": sum(1 for o, j in pairs if j >= 90 and o < 70),
        "tokens": session.meter.snapshot().get("total_tokens"),
        "note": "同一批回答两种口径并列：arm_gap 越大越能拉开好坏；judge_high_objective_low 是主观裁判放水的条数。",
    }
    store.write_json(store.run_dir(run_id) / "shadow.json", out)
    return out


@app.get("/api/run/{run_id}/reholdout")
async def get_reholdout(run_id: str) -> Any:
    """读已存的 holdout 复核结果（由 POST 同路径生成）。"""
    out = store.read_json(store.run_dir(run_id) / "reholdout.json")
    if out is None:
        raise HTTPException(404, "未做 holdout 复核（先 POST 同路径）")
    return out


@app.post("/api/run/{run_id}/reholdout")
async def post_reholdout(run_id: str, payload: dict[str, Any] = Body(default={})) -> Any:
    """只重跑 holdout 相位（默认重复 3 次），给出配对自助区间。

    原报告不动，结果落 `reholdout.json`。用途：旧 run 的 holdout 只跑了 1 次，
    Δ 的符号不稳定；重跑一次约 90s，比重跑整条流水线（约 10 分钟）便宜得多。
    """
    reps = max(1, min(8, int(payload.get("reps") or 3)))
    try:
        return await pipeline.reholdout(run_id, _key(payload.get("api_key")), reps=reps)
    except Budget as exc:
        # 额度耗尽 / Key 失效：说清楚是外部原因，别让调用方以为是这次 run 的数据有问题
        raise HTTPException(503, f"上游不可用，未写复核结果：{exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/run/{run_id}/abort")
async def abort_run(run_id: str) -> dict[str, Any]:
    if not MANAGER.abort(run_id):
        raise HTTPException(404, "run 不存在或已结束")
    return {"ok": True, "run_id": run_id}


@app.get("/api/case/{role_id}")
async def get_cases(role_id: str) -> Any:
    path = SETTINGS.data_dir / "case" / "role" / role_id / "testcases.jsonl"
    if not path.is_file():
        raise HTTPException(404, "题库不存在")
    items = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return {"role_id": role_id, "count": len(items), "items": items}


@app.exception_handler(Exception)
async def _unhandled(_request, exc: Exception) -> JSONResponse:  # noqa: ANN001
    return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)
