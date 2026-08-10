"""YiAgent factory demo API + static UI."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from evolve import EVOLVE_DIR, EVOLVE_MANAGER
import hof_ship
from jobs import MANAGER
from llm_client import model_ok as _model_ok, models_public
from case_library import LIBRARY
from preflight import run_preflight
from role_suite import (
    ROLE_MANAGER,
    count_suite_cases,
    list_blueprints,
    load_blueprint,
    load_bench_index,
    retrieve_anchors,
)
from testset import build_manifest, load_manifest, save_manifest

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "www"
log = logging.getLogger("factory")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="YiAgent Factory Demo", version="0.7.0")


def _http_from_exc(e: Exception, prefix: str) -> HTTPException:
    msg = f"{prefix}: {e}"
    log.error("%s\n%s", msg, traceback.format_exc())
    status = getattr(e, "status", None)
    if status in (400, 401, 403, 404, 422):
        return HTTPException(status, msg)
    return HTTPException(502, msg)


class CaseBody(BaseModel):
    api_key: str = Field(min_length=8)
    model: str = "k3"
    oral: str = Field(min_length=4)


class GenomesBody(BaseModel):
    api_key: str = Field(min_length=8)
    model: str | None = None


class CaseTextBody(BaseModel):
    target_text: str | None = None
    criteria_text: str | None = None


class BaselineBody(BaseModel):
    api_key: str = Field(min_length=8)
    baseline_reps: int = Field(default=5, ge=1, le=10)
    workers: int = Field(default=4, ge=1, le=12)
    model: str | None = None


class PrefilterBody(BaseModel):
    api_key: str = Field(min_length=8)
    pre_reps: int = Field(default=3, ge=1, le=10)
    qualify_target: int = Field(default=3, ge=1, le=20)
    pass_mean: float = Field(default=70.0, ge=0, le=100)
    workers: int = Field(default=4, ge=1, le=12)


class PoolBody(BaseModel):
    variant_ids: list[str]


class ChampionBody(BaseModel):
    api_key: str = Field(min_length=8)
    champ_reps: int = Field(default=5, ge=1, le=10)
    workers: int | None = None


class AutoBody(BaseModel):
    api_key: str = Field(min_length=8)
    model: str = "k3"
    source: str = Field(default="library", description="library|oral")
    suite: str | None = None
    id: str | None = None
    level: str = "basic"
    oral: str | None = None
    skip_baseline: bool = False
    baseline_reps: int = Field(default=5, ge=1, le=10)
    pre_reps: int = Field(default=3, ge=1, le=10)
    champ_reps: int = Field(default=5, ge=1, le=10)
    qualify_target: int = Field(default=3, ge=1, le=20)
    pass_mean: float = Field(default=70.0, ge=0, le=100)
    workers: int = Field(default=4, ge=1, le=12)
    champion_mark: str = Field(default="balanced", description="perf|stable|balanced")
    save: bool = True


class LoadSeedBody(BaseModel):
    pack: dict
    model: str = "k3"


class ImproveAutoBody(BaseModel):
    api_key: str = Field(min_length=8)
    pack: dict
    model: str = "k3"
    pre_reps: int = Field(default=3, ge=1, le=10)
    champ_reps: int = Field(default=5, ge=1, le=10)
    qualify_target: int = Field(default=3, ge=1, le=20)
    pass_mean: float = Field(default=70.0, ge=0, le=100)
    workers: int = Field(default=4, ge=1, le=12)
    champion_mark: str = Field(default="balanced", description="perf|stable|balanced")
    save: bool = True
    skip_refine: bool = False


@app.get("/api/health")
def health():
    return {"ok": True, "service": "yiagent-factory-demo", "version": "0.7.0"}


@app.get("/api/models")
def models():
    return {"models": models_public()}


@app.get("/api/cases/meta")
def cases_meta():
    return LIBRARY.meta()


@app.get("/api/cases")
def cases_list(
    suite: str | None = None,
    dimension: str | None = None,
    q: str | None = None,
    limit: int = 80,
    offset: int = 0,
):
    return LIBRARY.list_cases(
        suite=suite, dimension=dimension, q=q, limit=limit, offset=offset
    )


class LibraryCaseBody(BaseModel):
    suite: str = Field(min_length=1)
    id: str = Field(min_length=1)
    level: str = "basic"
    model: str = "k3"


@app.post("/api/session/case/library")
def session_case_library(body: LibraryCaseBody):
    """Load ready-made case from case/xsct — no LLM / API key required."""
    if body.model and not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.load_library_case(
            suite=body.suite.strip(),
            case_id=body.id.strip(),
            level=(body.level or "basic").strip(),
            model=body.model or "k3",
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "载入用例库失败") from e
    return sess.snapshot()


@app.post("/api/session/case")
def session_case(body: CaseBody):
    if not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.create_case(
            api_key=body.api_key.strip(), model=body.model, oral=body.oral.strip()
        )
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "生成题目失败") from e
    return sess.snapshot()


@app.post("/api/session/auto")
def session_auto(body: AutoBody):
    """Unattended full pipeline → best genome (default balanced mark)."""
    if not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.start_auto(
            api_key=body.api_key.strip(),
            model=body.model,
            source=body.source,
            suite=body.suite,
            case_id=body.id,
            level=body.level,
            oral=body.oral,
            skip_baseline=body.skip_baseline,
            baseline_reps=body.baseline_reps,
            pre_reps=body.pre_reps,
            champ_reps=body.champ_reps,
            qualify_target=body.qualify_target,
            pass_mean=body.pass_mean,
            workers=body.workers,
            champion_mark=body.champion_mark,
            do_save=body.save,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "全自动流水线启动失败") from e
    return sess.snapshot()


@app.post("/api/session/load-seed")
def session_load_seed(body: LoadSeedBody):
    """Load improve-pack / best_genome → genomes_ready (skip A/B)."""
    if body.model and not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.load_seed_pack(body.pack, model=body.model or "k3")
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "载入改进包失败") from e
    return sess.snapshot()


@app.post("/api/session/improve-auto")
def session_improve_auto(body: ImproveAutoBody):
    """Seed → refine → prefilter → champion → best genome."""
    if not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.start_improve_auto(
            api_key=body.api_key.strip(),
            pack=body.pack,
            model=body.model,
            pre_reps=body.pre_reps,
            champ_reps=body.champ_reps,
            qualify_target=body.qualify_target,
            pass_mean=body.pass_mean,
            workers=body.workers,
            champion_mark=body.champion_mark,
            do_save=body.save,
            skip_refine=body.skip_refine,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "一键改进启动失败") from e
    return sess.snapshot()


class DemoBody(BaseModel):
    fresh: bool = False  # True = fixture case for manual live run; False = prefer frozen pack


@app.post("/api/session/demo")
def session_demo(body: DemoBody = DemoBody()):
    """Load frozen pack (default) or fresh fixture case when fresh=True."""
    sess = MANAGER.hydrate_demo(fresh=body.fresh)
    return sess.snapshot()


@app.post("/api/session/{session_id}/bank/fixture")
def session_attach_bank(session_id: str):
    try:
        sess = MANAGER.attach_fixture_bank(session_id)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return sess.snapshot()


@app.get("/api/session/{session_id}/export")
def session_export(session_id: str):
    try:
        return MANAGER.export_pack(session_id)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class SaveBody(BaseModel):
    freeze_demo: bool = False
    label: str = "session"
    version_tag: str = "v1.0"


@app.post("/api/session/{session_id}/save")
def session_save(session_id: str, body: SaveBody = SaveBody()):
    """Persist pack + run log under save/; optional freeze to fixtures/demo_pack.json."""
    try:
        return MANAGER.save_session(
            session_id,
            freeze_demo=body.freeze_demo,
            label=body.label.strip() or "session",
            version_tag=body.version_tag.strip() or "v1.0",
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/session/{session_id}")
def session_get(session_id: str):
    sess = MANAGER.get(session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    return sess.snapshot()


@app.put("/api/session/{session_id}/case")
def session_update_case(session_id: str, body: CaseTextBody):
    try:
        sess = MANAGER.update_case_texts(
            session_id, target_text=body.target_text, criteria_text=body.criteria_text
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    return sess.snapshot()


@app.post("/api/session/{session_id}/baseline/start")
def session_baseline(session_id: str, body: BaselineBody):
    if body.model and not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.start_baseline(
            session_id,
            api_key=body.api_key.strip(),
            baseline_reps=body.baseline_reps,
            workers=body.workers,
            model=body.model,
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"session_id": sess.id, **sess.snapshot()}


@app.post("/api/session/{session_id}/baseline/skip")
def session_baseline_skip(session_id: str):
    try:
        sess = MANAGER.skip_baseline(session_id)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return sess.snapshot()


@app.post("/api/session/{session_id}/genomes")
def session_genomes(session_id: str, body: GenomesBody):
    if body.model and not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.generate_genomes(
            session_id, api_key=body.api_key.strip(), model=body.model
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "生成基因组失败") from e
    return sess.snapshot()


@app.post("/api/session/{session_id}/genomes/refine")
def session_genomes_refine(session_id: str, body: GenomesBody):
    if body.model and not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        sess = MANAGER.refine_session_genomes(
            session_id, api_key=body.api_key.strip(), model=body.model
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "邻域精炼基因组失败") from e
    return sess.snapshot()


@app.post("/api/session/{session_id}/prefilter/start")
def session_prefilter(session_id: str, body: PrefilterBody):
    try:
        sess = MANAGER.start_prefilter(
            session_id,
            api_key=body.api_key.strip(),
            pre_reps=body.pre_reps,
            qualify_target=body.qualify_target,
            pass_mean=body.pass_mean,
            workers=body.workers,
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"session_id": sess.id, **sess.snapshot()}


@app.post("/api/session/{session_id}/champion/pool")
def session_pool(session_id: str, body: PoolBody):
    try:
        sess = MANAGER.set_pool(session_id, body.variant_ids)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    return sess.snapshot()


@app.post("/api/session/{session_id}/champion/start")
def session_champion(session_id: str, body: ChampionBody):
    try:
        sess = MANAGER.start_champion(
            session_id,
            api_key=body.api_key.strip(),
            champ_reps=body.champ_reps,
            workers=body.workers,
        )
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"session_id": sess.id, **sess.snapshot()}


@app.post("/api/session/{session_id}/abort")
def session_abort(session_id: str):
    try:
        sess = MANAGER.abort(session_id)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    return sess.snapshot()


class TestsetManifestBody(BaseModel):
    demand: str = Field(min_length=1)
    suites: list[str] | None = None
    dimensions: list[str] | None = None
    q: str | None = None
    level: str = "basic"
    size: int = Field(default=10, ge=1, le=100)
    seed: int = 42
    holdout_ratio: float = Field(default=0.2, ge=0, le=0.5)
    ids: list[str] | None = None


@app.post("/api/testset/manifest")
def testset_manifest_create(body: TestsetManifestBody):
    """建测试集 manifest（进化集 + 分层 holdout）并落盘。无需 api_key。"""
    try:
        manifest = build_manifest(
            body.demand.strip(),
            suites=body.suites,
            dimensions=body.dimensions,
            q=body.q,
            level=body.level,
            size=body.size,
            seed=body.seed,
            holdout_ratio=body.holdout_ratio,
            ids=body.ids,
        )
        save_manifest(manifest)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "建测试集 manifest 失败") from e
    return manifest


@app.get("/api/testset/manifest/{manifest_id}")
def testset_manifest_get(manifest_id: str):
    try:
        return load_manifest(manifest_id)
    except KeyError:
        raise HTTPException(404, "manifest not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class RoleBuildBody(BaseModel):
    api_key: str = Field(min_length=8)
    model: str = "k3"
    role: str = Field(min_length=2, description="角色名，如「数据分析专家」")
    per_dim: int = Field(default=2, ge=1, le=4, description="每个能力维度出几道题")
    size: int = Field(default=10, ge=1, le=60, description="进化集题数上限")
    holdout_ratio: float = Field(default=0.3, ge=0, le=0.5)
    seed: int = 42
    replace: bool = True


@app.get("/api/role/anchors")
def role_anchors(role: str, q: str | None = None):
    """锚点检索：benchmark 策展索引 + 本地题库。不发 LLM、无需 api_key。"""
    queries = [x.strip() for x in (q or "").split(",") if x.strip()] or [role]
    return retrieve_anchors(queries, role=role)


@app.get("/api/role/benchmarks")
def role_benchmarks():
    """benchmark 策展索引全量（角色工厂的题型/判分口径参考来源）。"""
    return load_bench_index()


@app.get("/api/roles")
def roles_list():
    return {"ok": True, "roles": list_blueprints()}


@app.post("/api/role/build")
def role_build(body: RoleBuildBody):
    """角色名 → 能力维度蓝图 → 题组（含裁判）→ suite 落盘 → manifest。后台跑。

    完成后用返回的 manifest_id 调 POST /api/evolve/start 做基因搜索与 holdout 鉴定。
    """
    if not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        run = ROLE_MANAGER.start(
            body.api_key.strip(),
            body.model,
            body.role.strip(),
            per_dim=body.per_dim,
            size=body.size,
            holdout_ratio=body.holdout_ratio,
            seed=body.seed,
            replace=body.replace,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "角色题组构建启动失败") from e
    return run.snapshot()


@app.get("/api/role/build/{run_id}")
def role_build_get(run_id: str):
    run = ROLE_MANAGER.get(run_id)
    if not run:
        raise HTTPException(404, "role build not found")
    return run.snapshot()


@app.post("/api/role/build/{run_id}/abort")
def role_build_abort(run_id: str):
    try:
        run = ROLE_MANAGER.abort(run_id)
    except KeyError:
        raise HTTPException(404, "role build not found") from None
    return run.snapshot()


@app.get("/api/role/{role_id}")
def role_get(role_id: str):
    try:
        bp = load_blueprint(role_id)
    except KeyError:
        raise HTTPException(404, "blueprint not found") from None
    return {"ok": True, "blueprint": bp, "cases": count_suite_cases(role_id)}


class EvolveStartBody(BaseModel):
    api_key: str = Field(min_length=8)
    model: str = "k3"
    oral: str | None = None
    manifest_id: str | None = None
    manifest: dict | None = None
    seed: dict | None = None
    max_generations: int = Field(default=4, ge=1, le=10)
    variants_per_gen: int = Field(default=6, ge=2, le=12)
    eval_reps: int = Field(default=2, ge=1, le=10)
    final_reps: int = Field(default=3, ge=1, le=10)
    workers: int = Field(default=16, ge=1, le=64)
    pass_mean: float = Field(default=70.0, ge=0, le=100)
    elite_k: int = Field(default=2, ge=1, le=6)
    stagnation_limit: int = Field(default=2, ge=1, le=5)
    improve_threshold: float = Field(default=1.0, ge=0, le=20)
    max_tokens_budget: int | None = Field(default=None, ge=1000)
    anchor_case: dict | None = None
    with_baseline: bool = True
    use_cache: bool = True


@app.post("/api/evolve/start")
def evolve_start(body: EvolveStartBody):
    """批量鉴定 + 多代进化：manifest 测试集 × 基因组 bank，后台跑。"""
    if not _model_ok(body.model):
        raise HTTPException(400, f"model not supported: {body.model}")
    try:
        run = EVOLVE_MANAGER.start(
            body.api_key.strip(),
            body.model,
            manifest_id=body.manifest_id,
            manifest=body.manifest,
            oral=body.oral,
            seed=body.seed,
            max_generations=body.max_generations,
            variants_per_gen=body.variants_per_gen,
            eval_reps=body.eval_reps,
            final_reps=body.final_reps,
            workers=body.workers,
            pass_mean=body.pass_mean,
            elite_k=body.elite_k,
            stagnation_limit=body.stagnation_limit,
            improve_threshold=body.improve_threshold,
            max_tokens_budget=body.max_tokens_budget,
            anchor_case=body.anchor_case,
            with_baseline=body.with_baseline,
            use_cache=body.use_cache,
        )
    except KeyError:
        raise HTTPException(404, "manifest not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "进化启动失败") from e
    snap = run.snapshot()
    # 附带起飞前检查结果（保守默认：只提示不阻断，含 errors 也不阻断——
    # manifest/key 类硬失败本身会在 start 里先抛错）
    try:
        snap["preflight"] = run_preflight(
            manifest_id=body.manifest_id or (run.manifest_id or None),
            manifest=body.manifest,
            api_key=body.api_key.strip(),
            params=dict(run.params),
        )
    except Exception:  # noqa: BLE001
        snap["preflight"] = {
            "ok": True,
            "errors": [],
            "warnings": ["preflight 自身异常，已忽略（不影响 run）"],
            "checks": {},
        }
    return snap


@app.get("/api/evolve/preflight")
def evolve_preflight(manifest_id: str | None = None):
    """起飞前检查：题库/密钥/HOF/缓存/预算体检。不发 LLM、不读密钥内容。

    注意注册顺序：必须位于 /api/evolve/{run_id} 之前，否则被路径参数路由吃掉。
    """
    return run_preflight(manifest_id=manifest_id)


@app.get("/api/evolve/{run_id}")
def evolve_get(run_id: str):
    run = EVOLVE_MANAGER.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run.snapshot()


@app.post("/api/evolve/{run_id}/abort")
def evolve_abort(run_id: str):
    try:
        run = EVOLVE_MANAGER.abort(run_id)
    except KeyError:
        raise HTTPException(404, "run not found") from None
    return run.snapshot()


@app.get("/api/evolve/{run_id}/report")
def evolve_report(run_id: str):
    import json

    path = EVOLVE_DIR / run_id / "report.json"
    if not path.is_file():
        raise HTTPException(404, "report not ready")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/hof/status")
def hof_status():
    """名人堂上报状态（默认关闭，严格 opt-in）。"""
    return hof_ship.status()


@app.get("/api/hof/dry-run/{run_id}")
def hof_dry_run(run_id: str):
    """查看"如果开启会上报什么"（redact 后的 payload），不发网络。"""
    run_dir = EVOLVE_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(404, "run not found")
    try:
        return {"run_id": run_id, "submissions": hof_ship.dry_run(run_dir)}
    except FileNotFoundError:
        raise HTTPException(404, "report not ready") from None
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "构造上报 payload 失败") from e


@app.post("/api/hof/ship/{run_id}")
def hof_ship_run(run_id: str):
    """手动触发上报该 run（需先开启 YIAGENT_HOF_ENABLED），并尝试 flush 队列。"""
    if not hof_ship.enabled():
        raise HTTPException(
            400,
            "名人堂上报未开启：设置环境变量 YIAGENT_HOF_ENABLED=true "
            "（可选 YIAGENT_HOF_URL）后重启服务再试",
        )
    run_dir = EVOLVE_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(404, "run not found")
    try:
        payloads = hof_ship.build_submissions(
            run_dir, contributor_id=hof_ship.contributor_id()
        )
    except FileNotFoundError:
        raise HTTPException(404, "report not ready") from None
    except Exception as e:  # noqa: BLE001
        raise _http_from_exc(e, "构造上报 payload 失败") from e
    if not payloads:
        raise HTTPException(400, "no submissions built from this run")
    result = hof_ship.ship(payloads, base_url=hof_ship.base_url())
    result["flush"] = hof_ship.flush_queue()
    return result


@app.get("/")
def index():
    return FileResponse(WWW / "index.html")


@app.get("/{path:path}")
def static_or_spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "not found")
    for base in (WWW, ROOT):
        candidate = base / path
        if candidate.is_file():
            return FileResponse(candidate)
    return FileResponse(WWW / "index.html")
