"""名人堂（Hall of Fame）上报客户端 —— 严格 opt-in，默认零网络行为。

数据流：evolve run 产物（report.json + 各代 scorecard）→ build_submissions
→ redact（白名单制，只保留 schema 声明字段）→ ship（POST /api/hof/submit，
批量 {"submissions": [...]}）→ 失败落本地队列 save/ship_queue/ 待 flush_queue 重试。

配置：环境变量 YIAGENT_HOF_ENABLED（默认 false）/ YIAGENT_HOF_URL
（默认 http://localhost:8788）；contributor_id 持久化在 save/hof_identity.json。
payload schema 见 docs/20260731_名人堂服务规划.md 第三节。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from eval_cache import cache_stats, gene_hash_of

ROOT = Path(__file__).resolve().parents[1]
SAVE_DIR = ROOT / "save"
QUEUE_DIR = SAVE_DIR / "ship_queue"
IDENTITY_FILE = SAVE_DIR / "hof_identity.json"

log = logging.getLogger("factory.hof")

SCHEMA = "yiagent.hof.submission"
SCHEMA_VERSION = "0.1"
DEFAULT_URL = "http://localhost:8788"
DEFAULT_YIAGENT_VERSION = "0.2.0"

# redact 白名单：只允许这些字段路径通过（· 表示嵌套，* 表示列表元素下同）。
# 未列出的字段（api_key / 本地路径 / message 全文 / preview 等）一律丢弃。
_WHITELIST = (
    "schema",
    "version",
    "contributor_id",
    "submitted_at",
    "genome",
    "genome.gene_hash",
    "genome.bank",
    "genome.variant_id",
    "evaluation",
    "evaluation.model",
    "evaluation.testset",
    "evaluation.reps",
    "evaluation.stats",
    "evaluation.per_case",
    "evaluation.dim_means",
    "context",
    "context.yiagent_version",
    "context.evolve",
    "context.demand_tags",
)


def enabled() -> bool:
    return os.environ.get("YIAGENT_HOF_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def base_url() -> str:
    return (os.environ.get("YIAGENT_HOF_URL") or DEFAULT_URL).rstrip("/")


def contributor_id() -> str:
    """匿名贡献者 ID：首次随机生成 anon_+hex 并持久化，删 save/hof_identity.json 可重置。"""
    if IDENTITY_FILE.is_file():
        try:
            cid = str(json.loads(IDENTITY_FILE.read_text(encoding="utf-8")).get("contributor_id") or "")
            if cid:
                return cid
        except (OSError, ValueError):
            pass
    cid = f"anon_{uuid.uuid4().hex[:12]}"
    try:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        IDENTITY_FILE.write_text(
            json.dumps({"contributor_id": cid}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        log.warning("hof: persist contributor_id failed", exc_info=True)
    return cid


def status() -> dict[str, Any]:
    return {
        "enabled": enabled(),
        "url": base_url(),
        "contributor_id": contributor_id(),
        "queue_size": queue_size(),
        "cache": cache_stats(),
    }


def queue_size() -> int:
    if not QUEUE_DIR.is_dir():
        return 0
    return len(list(QUEUE_DIR.glob("*.json")))


# ---- payload 构造 ----


def _run_id_hash(run_id: str) -> str:
    return hashlib.sha256(str(run_id).encode("utf-8")).hexdigest()[:16]


def _dim_means(scorecard: dict) -> dict[str, float]:
    acc: dict[str, list[float]] = {}
    for case in scorecard.get("cases") or []:
        for dim, val in (case.get("dimension_scores") or {}).items():
            try:
                acc.setdefault(dim, []).append(float(val))
            except (TypeError, ValueError):
                continue
    return {d: round(sum(v) / len(v), 2) for d, v in acc.items() if v}


def _submission(
    *,
    scorecard: dict,
    variant: dict,
    bank: dict,
    model: str,
    generation: int,
    run_id: str,
    contributor: str,
    yiagent_version: str,
) -> dict:
    """单份 submission（schema: yiagent.hof.submission）。testset 只传公共题引用。"""
    cases = [
        {"suite": c.get("suite"), "id": c.get("id"), "level": c.get("level")}
        for c in scorecard.get("cases") or []
    ]
    per_case = [
        {
            "suite": c.get("suite"),
            "id": c.get("id"),
            "mean": (c.get("stats") or {}).get("mean"),
            "sdv": (c.get("stats") or {}).get("sdv"),
        }
        for c in scorecard.get("cases") or []
    ]
    dim_means = _dim_means(scorecard)
    variant_id = str(scorecard.get("variant_id") or variant.get("id") or "")
    return {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "contributor_id": contributor,
        "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "genome": {
            "gene_hash": gene_hash_of(variant),
            "bank": {
                "alleles": (bank or {}).get("alleles") or {},
                "variants": [variant],
            },
            "variant_id": variant_id,
        },
        "evaluation": {
            "model": model,
            "testset": {"kind": "xsct", "cases": cases},
            "reps": int(scorecard.get("reps") or 0),
            "stats": {
                "mean": scorecard.get("mean"),
                "sdv": scorecard.get("sdv"),
                "composite": scorecard.get("composite"),
                "n": scorecard.get("n"),
            },
            "per_case": per_case,
            "dim_means": dim_means,
        },
        "context": {
            "yiagent_version": yiagent_version,
            "evolve": {"generation": generation, "run_id_hash": _run_id_hash(run_id)},
            "demand_tags": sorted(dim_means.keys()),
        },
    }


def _reconstruct_variant(scorecard: dict, bank: dict) -> dict:
    """评分卡里的 slots/title + bank 中现存 variant 信息 → 上报用 variant。"""
    vid = str(scorecard.get("variant_id") or "")
    for v in (bank or {}).get("variants") or []:
        if str(v.get("id")) == vid:
            return dict(v)
    return {
        "id": vid,
        "title": scorecard.get("title") or vid,
        "hash": scorecard.get("hash"),
        "slots": dict(scorecard.get("slots") or {}),
    }


def build_submissions(
    run_dir: Path, *, contributor_id: str, yiagent_version: str = DEFAULT_YIAGENT_VERSION
) -> list[dict]:
    """从 save/evolve/{run_id}/ 产物构造上报 payload：跨代总冠军 + 各代冠军。

    gene_hash 为去重主键：同哈希只报一份（总冠军优先于同哈希的代冠军）。
    """
    run_dir = Path(run_dir)
    report_path = run_dir / "report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"report not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model = str(report.get("model") or "")
    run_id = str(report.get("run_id") or run_dir.name)
    champ = report.get("champion") or {}
    final_bank = champ.get("bank") or {}

    # (generation, variant_id) 候选：总冠军在前（优先占位 gene_hash）
    candidates: list[tuple[int, str]] = []
    if champ.get("variant_id"):
        candidates.append((int(champ.get("gen") or 0), str(champ["variant_id"])))
    for row in report.get("champion_curve") or []:
        if row.get("variant_id"):
            candidates.append((int(row.get("gen") or 0), str(row["variant_id"])))

    out: list[dict] = []
    seen_hashes: set[str] = set()
    for gen, vid in candidates:
        card_path = run_dir / f"gen{gen}" / f"scorecard_{vid}.json"
        if not card_path.is_file():
            continue
        scorecard = json.loads(card_path.read_text(encoding="utf-8"))
        variant = _reconstruct_variant(scorecard, final_bank)
        gh = gene_hash_of(variant)
        if gh in seen_hashes:
            continue
        seen_hashes.add(gh)
        out.append(
            _submission(
                scorecard=scorecard,
                variant=variant,
                bank=final_bank,
                model=model,
                generation=gen,
                run_id=run_id,
                contributor=contributor_id,
                yiagent_version=yiagent_version,
            )
        )
    return out


def redact(payload: dict) -> dict:
    """白名单过滤：只保留 schema 声明的字段路径，其余一律丢弃。

    叶子路径（如 genome.bank、evaluation.stats）整体保留其子树；
    容器路径（如 genome、evaluation）逐字段递归过滤。
    """
    leaves = {
        w for w in _WHITELIST if not any(o.startswith(w + ".") for o in _WHITELIST)
    }
    containers = set(_WHITELIST) - leaves

    def walk(node: Any, prefix: str) -> Any:
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                path = f"{prefix}.{k}" if prefix else str(k)
                if path in leaves:
                    out[k] = v
                elif path in containers:
                    out[k] = walk(v, path)
            return out
        if isinstance(node, list):
            return [walk(item, prefix) for item in node]
        return node

    return walk(payload, "")


def dry_run(run_dir: Path, *, yiagent_version: str = DEFAULT_YIAGENT_VERSION) -> list[dict]:
    """返回"如果开启会上报什么"（redact 后的完整 payload），不发网络。"""
    payloads = build_submissions(
        Path(run_dir), contributor_id=contributor_id(), yiagent_version=yiagent_version
    )
    return [redact(p) for p in payloads]


# ---- 网络与队列 ----


def _post_json(url: str, body: dict, timeout: float) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read().decode("utf-8") or "{}"
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw}


def _enqueue(payloads: list[dict], *, url: str) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = QUEUE_DIR / f"{stamp}_{uuid.uuid4().hex[:6]}.json"
    path.write_text(
        json.dumps({"url": url, "payloads": payloads}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def ship(payloads: list[dict], *, base_url: str, timeout: float = 10) -> dict:
    """批量 POST {base_url}/api/hof/submit，body = {"submissions": [...]}。

    失败写本地队列 save/ship_queue/{ts}.json，由 flush_queue() 重试。
    """
    url = f"{base_url.rstrip('/')}/api/hof/submit"
    clean = [redact(p) for p in payloads]
    body = {"schema": "yiagent.hof.batch", "submissions": clean}
    try:
        resp = _post_json(url, body, timeout)
        return {"ok": True, "url": url, "submitted": len(clean), "response": resp}
    except Exception as e:  # noqa: BLE001
        path = _enqueue(clean, url=url)
        log.warning("hof: ship failed, queued to %s: %s", path, e)
        return {
            "ok": False,
            "url": url,
            "submitted": 0,
            "queued": str(path),
            "error": str(e),
        }


def flush_queue(*, timeout: float = 10) -> dict:
    """重试本地队列：成功则删除队列文件。"""
    sent = 0
    failed = 0
    if QUEUE_DIR.is_dir():
        for path in sorted(QUEUE_DIR.glob("*.json")):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                body = {
                    "schema": "yiagent.hof.batch",
                    "submissions": item.get("payloads") or [],
                }
                _post_json(str(item.get("url") or f"{base_url()}/api/hof/submit"), body, timeout)
                path.unlink()
                sent += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                log.warning("hof: flush %s failed: %s", path, e)
    return {"sent": sent, "failed": failed, "remaining": queue_size()}


def auto_ship_run(run_dir: Path, *, timeout: float = 10) -> dict:
    """evolve run 结束后的自动上报钩子：未 enabled 直接跳过；异常只记日志。"""
    if not enabled():
        return {"ok": False, "skipped": True, "reason": "YIAGENT_HOF_ENABLED not set"}
    try:
        payloads = build_submissions(Path(run_dir), contributor_id=contributor_id())
        if not payloads:
            return {"ok": False, "skipped": True, "reason": "no submissions built"}
        result = ship(payloads, base_url=base_url(), timeout=timeout)
        result["flush"] = flush_queue(timeout=timeout)
        return result
    except Exception as e:  # noqa: BLE001
        log.error("hof: auto ship failed (run 不受影响): %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}
