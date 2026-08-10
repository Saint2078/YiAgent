from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import executor, pipeline, sample50
from .config import settings

app = FastAPI(title="YiAgent codebench", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allow_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExecBody(BaseModel):
    code: str = Field(..., min_length=1)
    tests: str = Field(..., min_length=1)
    language: str = "python"
    timeout_s: float | None = None


class RunBody(BaseModel):
    limit: int | None = Field(default=None, description="调试用：只跑前 N 题；正式榜留空=50")
    role_id: str = Field(default="coding_board_racer", description="coding_board_racer | coding_board_bare")
    rebuild_sample: bool = False


class CompareBody(BaseModel):
    limit: int | None = Field(default=None, description="调试用：每臂前 N 题")
    rebuild_sample: bool = Field(default=True, description="对照跑默认重建 r2 抽样")


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": "codebench",
        "goal": "GOAL-CODEBENCH-B-001",
        "milestone": "M2",
        "role": "coding_board_racer",
        "bare_role": "coding_board_bare",
    }


@app.get("/api/goal")
def goal():
    return {
        "goal_id": "GOAL-CODEBENCH-B-001",
        "model": "kimi_only",
        "sample_n": 50,
        "dataset": "LiveCodeBench codegeneration release_v5 (stratified sample)",
        "tests": "public_and_private",
        "ui": "console 榜单区 · 编程榜",
        "role": "coding_board_racer",
        "bare_role": "coding_board_bare",
        "milestones": ["M0_executor", "M1_sample50_kimi", "M2_board_page", "M3_genome_vs_bare"],
    }


@app.get("/api/role")
def role(role_id: str = "coding_board_racer"):
    try:
        return pipeline.load_role(role_id)
    except Exception as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/exec")
def exec_code(body: ExecBody):
    if body.language != "python":
        return {"ok": False, "error": "only_python_in_m0", "language": body.language}
    timeout = body.timeout_s if body.timeout_s is not None else settings.exec_timeout_s
    result = executor.run_python(
        body.code,
        body.tests,
        timeout_s=timeout,
        mem_mb=settings.mem_mb,
    )
    return {"language": "python", "timeout_s": timeout, **result}


@app.post("/api/sample/build")
def sample_build():
    try:
        out = pipeline.sample50_path()
        meta = sample50.build_sample(out)
        return {"ok": True, "meta": meta, "path": str(out)}
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@app.get("/api/sample")
def sample_meta():
    p = pipeline.sample_path()
    if not p.exists():
        return {"ok": False, "built": False}
    data = sample50.load_sample(p)
    return {"ok": True, "built": True, "meta": data.get("meta"), "n": len(data.get("problems") or [])}


@app.post("/api/run")
def run_start(body: RunBody | None = None):
    body = body or RunBody()
    try:
        pipeline.load_role(body.role_id)
    except Exception as e:
        raise HTTPException(500, f"role_missing:{e}") from e
    run_id = pipeline.start_run(
        limit=body.limit,
        role_id=body.role_id,
        rebuild_sample=body.rebuild_sample,
    )
    return {"ok": True, "run_id": run_id, "role_id": body.role_id}


@app.post("/api/run/compare")
def run_compare(body: CompareBody | None = None):
    body = body or CompareBody()
    try:
        pipeline.load_role(pipeline.DEFAULT_ROLE)
        pipeline.load_role(pipeline.BARE_ROLE)
    except Exception as e:
        raise HTTPException(500, f"role_missing:{e}") from e
    run_id = pipeline.start_compare(limit=body.limit, rebuild_sample=body.rebuild_sample)
    return {"ok": True, "run_id": run_id, "mode": "compare"}


@app.get("/api/runs")
def runs():
    return {"runs": pipeline.list_runs()}


@app.get("/api/run/{run_id}")
def run_get(run_id: str):
    r = pipeline.get_run(run_id)
    if not r:
        report = Path(settings.data_dir) / "runs" / run_id / "report.json"
        compare = Path(settings.data_dir) / "runs" / run_id / "compare.json"
        if compare.exists():
            import json

            return json.loads(compare.read_text(encoding="utf-8"))
        if report.exists():
            import json

            return json.loads(report.read_text(encoding="utf-8"))
        raise HTTPException(404, "run_not_found")
    return r


@app.get("/api/report/latest")
def report_latest():
    p = Path(settings.data_dir) / "latest_report.json"
    if not p.exists():
        return {"ok": False, "report": None}
    import json

    return {"ok": True, "report": json.loads(p.read_text(encoding="utf-8"))}


@app.get("/api/report/compare")
def report_compare():
    p = Path(settings.data_dir) / "latest_compare.json"
    if not p.exists():
        return {"ok": False, "compare": None}
    import json

    return {"ok": True, "compare": json.loads(p.read_text(encoding="utf-8"))}
