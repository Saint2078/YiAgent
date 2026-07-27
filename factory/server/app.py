"""YiAgent factory demo API + static UI."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from jobs import MANAGER

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "www"
log = logging.getLogger("factory")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="YiAgent Factory Demo", version="0.4.0")

MODELS = [
    {"id": "k3", "label": "Kimi 3", "provider": "kimi-coding", "supported": True},
    {"id": "kimi-k2.6", "label": "Kimi 2.6", "provider": "kimi-coding", "supported": True},
]


def _model_ok(model: str) -> bool:
    m = next((x for x in MODELS if x["id"] == model), None)
    return bool(m and m["supported"])


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


@app.get("/api/health")
def health():
    return {"ok": True, "service": "yiagent-factory-demo", "version": "0.4.0"}


@app.get("/api/models")
def models():
    return {"models": MODELS}


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
