"""YiAgent 名人堂（Hall of Fame）服务：ingest + 聚合 + 读 API + 静态工作台。

契约见 docs/20260731_名人堂服务规划.md 第三节（payload schema）。
独立运行，不 import factory 代码；数据落 SQLite（默认 hof/data/hof.db）。
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from store import Store

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "www"
DEFAULT_DB = ROOT / "data" / "hof.db"
log = logging.getLogger("hof")
logging.basicConfig(level=logging.INFO)

VERSION = "0.1.0"
SCHEMA_NAME = "yiagent.hof.submission"
SCHEMA_VERSION = "0.1"

# ---- 体量上限（规划文档第五节：严格 schema + 字段长度上限） ----
MAX_BATCH = 200
MAX_BODY_BYTES = 512 * 1024
MAX_ID_LEN = 128          # contributor_id / gene_hash / variant_id / model
MAX_TAG_LEN = 64
MAX_TAGS = 20
MAX_LABEL_LEN = 200
MAX_TEXT_LEN = 4000       # 单条等位文本
MAX_CASES = 500
MAX_DIMS = 50

# ---- 反作弊：等位文本里灌评分标准/rubric 等于作弊，违例拒收 ----
RUBRIC_KEYWORDS = (
    "rubric",
    "评分标准",
    "评分细则",
    "评分量表",
    "打分标准",
    "打分规则",
    "评分维度",
    "scoring criteria",
    "grading rubric",
)

# ---- 服务端白名单（多余字段丢弃并记录，与客户端 redaction 对齐） ----
TOP_KEYS = {"schema", "version", "contributor_id", "submitted_at", "genome", "evaluation", "context"}
GENOME_KEYS = {"gene_hash", "bank", "variant_id"}
BANK_KEYS = {"alleles", "variants"}
ALLELE_KEYS = {"id", "label", "text"}
VARIANT_KEYS = {"id", "title", "hash", "slots"}
EVAL_KEYS = {"model", "testset", "reps", "stats", "per_case", "dim_means"}
STATS_KEYS = {"mean", "sdv", "composite", "n"}
TESTSET_KEYS = {"kind", "cases"}
CASE_KEYS = {"suite", "id", "level", "mean", "sdv"}
CONTEXT_KEYS = {"yiagent_version", "evolve", "demand_tags"}

# ---- 限流：同一 contributor 每分钟最多 30 份（内存计数） ----
RATE_LIMIT = 30
RATE_WINDOW = 60.0


def _clip_str(val: Any, limit: int) -> str:
    return str(val)[:limit] if val is not None else ""


def _whitelist(obj: Any, allowed: set[str], dropped: list[str], path: str) -> Any:
    if not isinstance(obj, dict):
        return obj
    out = {}
    for key, val in obj.items():
        if key in allowed:
            out[key] = val
        else:
            dropped.append(f"{path}.{key}" if path else str(key))
    return out


def _clean_genome(genome: Any, dropped: list[str]) -> dict:
    """白名单清洗 genome，同时对等位文本做 rubric 关键词检测。返回 (clean, cheat_hit)。"""
    if not isinstance(genome, dict):
        return {}, ""
    clean = _whitelist(genome, GENOME_KEYS, dropped, "genome")
    bank = clean.get("bank")
    if isinstance(bank, dict):
        bank = _whitelist(bank, BANK_KEYS, dropped, "genome.bank")
        alleles = bank.get("alleles")
        if isinstance(alleles, dict):
            clean_alleles = {}
            for slot, items in alleles.items():
                if not isinstance(items, list):
                    continue
                slot_items = []
                for a in items[:200]:
                    if not isinstance(a, dict):
                        continue
                    a = _whitelist(a, ALLELE_KEYS, dropped, f"genome.bank.alleles.{slot}")
                    a["id"] = _clip_str(a.get("id"), MAX_ID_LEN)
                    a["label"] = _clip_str(a.get("label"), MAX_LABEL_LEN)
                    a["text"] = _clip_str(a.get("text"), MAX_TEXT_LEN)
                    slot_items.append(a)
                    lowered = (a["text"] or "").lower()
                    for kw in RUBRIC_KEYWORDS:
                        if kw.lower() in lowered:
                            return {}, f"等位文本含评分标准关键词「{kw}」（slot {slot}，疑似灌 rubric 作弊）"
                clean_alleles[str(slot)] = slot_items
            bank["alleles"] = clean_alleles
        variants = bank.get("variants")
        if isinstance(variants, list):
            bank["variants"] = [
                _whitelist(v, VARIANT_KEYS, dropped, "genome.bank.variants")
                for v in variants[:50]
                if isinstance(v, dict)
            ]
        clean["bank"] = bank
    if clean.get("gene_hash") is not None:
        clean["gene_hash"] = _clip_str(clean.get("gene_hash"), MAX_ID_LEN)
    if clean.get("variant_id") is not None:
        clean["variant_id"] = _clip_str(clean.get("variant_id"), MAX_ID_LEN)
    return clean, ""


def validate_submission(raw: Any) -> tuple[dict | None, str, list[str]]:
    """校验 + 白名单清洗一份上报。返回 (clean_payload, reject_reason, dropped_fields)。"""
    dropped: list[str] = []
    if not isinstance(raw, dict):
        return None, "payload 不是 JSON 对象", dropped
    if len(json.dumps(raw, ensure_ascii=False, default=str)) > MAX_BODY_BYTES:
        return None, f"单份 payload 超过 {MAX_BODY_BYTES // 1024}KB 上限", dropped

    if raw.get("schema") != SCHEMA_NAME:
        return None, f"schema 必须为 {SCHEMA_NAME}", dropped
    if str(raw.get("version")) != SCHEMA_VERSION:
        return None, f"version 必须为 {SCHEMA_VERSION}（收到 {raw.get('version')!r}）", dropped

    contributor_id = raw.get("contributor_id")
    if not contributor_id or not isinstance(contributor_id, str):
        return None, "缺少 contributor_id", dropped
    if len(contributor_id) > MAX_ID_LEN:
        return None, f"contributor_id 超过 {MAX_ID_LEN} 字符上限", dropped

    clean = _whitelist(raw, TOP_KEYS, dropped, "")
    clean["contributor_id"] = contributor_id
    if clean.get("submitted_at") is not None:
        clean["submitted_at"] = _clip_str(clean.get("submitted_at"), 64)

    genome, cheat = _clean_genome(raw.get("genome"), dropped)
    if cheat:
        return None, cheat, dropped
    if not genome.get("gene_hash"):
        return None, "缺少 genome.gene_hash", dropped
    bank = genome.get("bank")
    if not isinstance(bank, dict) or not isinstance(bank.get("alleles"), dict):
        return None, "缺少 genome.bank.alleles", dropped
    clean["genome"] = genome

    ev = _whitelist(raw.get("evaluation") if isinstance(raw.get("evaluation"), dict) else {},
                    EVAL_KEYS, dropped, "evaluation")
    model = ev.get("model")
    if not model or not isinstance(model, str):
        return None, "缺少 evaluation.model", dropped
    if len(model) > MAX_ID_LEN:
        return None, f"evaluation.model 超过 {MAX_ID_LEN} 字符上限", dropped
    stats = _whitelist(ev.get("stats") if isinstance(ev.get("stats"), dict) else {},
                       STATS_KEYS, dropped, "evaluation.stats")
    try:
        stats["mean"] = float(stats["mean"])
        stats["sdv"] = float(stats["sdv"])
        stats["composite"] = float(stats["composite"])
        stats["n"] = int(stats["n"])
    except (KeyError, TypeError, ValueError):
        return None, "evaluation.stats 需含数值型 mean/sdv/composite/n", dropped
    if stats["n"] < 1 or stats["n"] > 1_000_000:
        return None, "evaluation.stats.n 超出合法范围 [1, 1000000]", dropped
    for key in ("mean", "composite"):
        if not 0.0 <= stats[key] <= 100.0:
            return None, f"evaluation.stats.{key} 需在 [0, 100]", dropped
    if stats["sdv"] < 0 or stats["sdv"] > 100:
        return None, "evaluation.stats.sdv 需在 [0, 100]", dropped
    ev["stats"] = stats

    testset = ev.get("testset")
    if isinstance(testset, dict):
        testset = _whitelist(testset, TESTSET_KEYS, dropped, "evaluation.testset")
        cases = testset.get("cases")
        if isinstance(cases, list):
            testset["cases"] = [
                _whitelist(c, CASE_KEYS, dropped, "evaluation.testset.cases")
                for c in cases[:MAX_CASES]
                if isinstance(c, dict)
            ]
        ev["testset"] = testset
    per_case = ev.get("per_case")
    if isinstance(per_case, list):
        ev["per_case"] = [
            _whitelist(c, CASE_KEYS, dropped, "evaluation.per_case")
            for c in per_case[:MAX_CASES]
            if isinstance(c, dict)
        ]
    dims = ev.get("dim_means")
    if isinstance(dims, dict):
        clean_dims = {}
        for k, v in list(dims.items())[:MAX_DIMS]:
            try:
                clean_dims[_clip_str(k, MAX_TAG_LEN)] = float(v)
            except (TypeError, ValueError):
                continue
        ev["dim_means"] = clean_dims
    clean["evaluation"] = ev

    ctx = _whitelist(raw.get("context") if isinstance(raw.get("context"), dict) else {},
                     CONTEXT_KEYS, dropped, "context")
    tags = ctx.get("demand_tags")
    if isinstance(tags, list):
        ctx["demand_tags"] = [_clip_str(t, MAX_TAG_LEN) for t in tags[:MAX_TAGS]]
    clean["context"] = ctx
    return clean, "", dropped


class RateLimiter:
    """同一 contributor 每分钟最多 RATE_LIMIT 份（内存滑动窗口）。"""

    def __init__(self, limit: int = RATE_LIMIT, window: float = RATE_WINDOW):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, contributor_id: str) -> bool:
        now = time.monotonic()
        q = self._hits[contributor_id]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def create_app(db_path: str | Path | None = None) -> FastAPI:
    store = Store(db_path or os.environ.get("HOF_DB_PATH") or DEFAULT_DB)
    limiter = RateLimiter()
    app = FastAPI(title="YiAgent Hall of Fame", version=VERSION)
    app.state.store = store

    @app.get("/api/health")
    def health():
        return {"ok": True, "service": "yiagent-hof", "version": VERSION}

    @app.post("/api/hof/submit")
    async def submit(request: Request):
        try:
            body = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            raise HTTPException(400, "请求体不是合法 JSON")
        # 兼容单份直接 POST 与 {"submissions": [...]} 批量
        if isinstance(body, dict) and isinstance(body.get("submissions"), list):
            items = body["submissions"]
        elif isinstance(body, dict):
            items = [body]
        else:
            raise HTTPException(400, "请求体需为单份上报对象或 {submissions: [...]}")
        if len(items) > MAX_BATCH:
            raise HTTPException(413, f"批量最多 {MAX_BATCH} 份")

        results = []
        rate_limited = 0
        for raw in items:
            clean, reason, dropped = validate_submission(raw)
            contributor = ""
            gene_hash = ""
            if isinstance(raw, dict):
                contributor = str(raw.get("contributor_id") or "")
                gene_hash = str((raw.get("genome") or {}).get("gene_hash") or "")
            entry = {"gene_hash": gene_hash, "status": "rejected", "reason": reason}
            if clean is None:
                if contributor:
                    store.record_submission(
                        {"contributor_id": contributor, "genome": {"gene_hash": gene_hash},
                         "evaluation": {}},
                        status="rejected", reason=reason,
                    )
                results.append(entry)
                continue
            contributor = clean["contributor_id"]
            entry["gene_hash"] = clean["genome"]["gene_hash"]
            if not limiter.allow(contributor):
                entry["reason"] = f"rate_limited：每分钟最多 {limiter.limit} 份"
                rate_limited += 1
                store.record_submission(clean, status="rejected", reason=entry["reason"])
                results.append(entry)
                continue
            store.record_submission(clean, status="accepted")
            entry["status"] = "accepted"
            entry["reason"] = ""
            if dropped:
                entry["dropped_fields"] = dropped
                log.warning("submission 多余字段已丢弃: %s", dropped)
            results.append(entry)

        accepted = sum(1 for r in results if r["status"] == "accepted")
        payload = {
            "ok": True,
            "received": len(results),
            "accepted": accepted,
            "rejected": len(results) - accepted,
            "results": results,
        }
        # 整批都被限流 → 429；部分拒收仍 200（逐份原因见 results）
        if results and rate_limited == len(results):
            return JSONResponse(payload, status_code=429)
        return payload

    @app.get("/api/hof/leaderboard")
    def leaderboard(dimension: str = "", model: str = "", suite: str = "",
                    min_n: int = 3, limit: int = 50):
        min_n = max(0, min(min_n, 10_000))
        limit = max(1, min(limit, 500))
        return {
            "min_n": min_n,
            "shrink": {"m": 5.0, "prior": 75.0},
            "items": store.leaderboard(
                dimension=dimension, model=model, suite=suite, min_n=min_n, limit=limit,
            ),
        }

    @app.get("/api/hof/genome/{gene_hash}")
    def genome(gene_hash: str):
        item = store.get_genome(gene_hash)
        if item is None:
            raise HTTPException(404, f"genome 不存在: {gene_hash}")
        return item

    @app.get("/api/hof/alleles")
    def alleles(slot: str = "", limit: int = 50):
        limit = max(1, min(limit, 500))
        return {"slot": slot or None, "items": store.allele_performance(slot=slot, limit=limit)}

    @app.get("/api/hof/stats")
    def stats():
        return store.stats()

    @app.get("/api/hof/submissions")
    def submissions(limit: int = 50):
        limit = max(1, min(limit, 500))
        return {"items": store.recent_submissions(limit=limit)}

    if WWW.is_dir():
        app.mount("/", StaticFiles(directory=str(WWW), html=True), name="www")
    return app


app = create_app()
