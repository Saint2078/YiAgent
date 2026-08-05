"""本地评估缓存（名人堂归档的本地版）。

key = (gene_hash, model, suite, case_id, level)；value = {scores, mean, sdv, n, updated_at}。
按 variant 分文件落盘 save/eval_cache/{gene_hash[:16]}.json，避免单文件膨胀与锁竞争。
schema 与名人堂上报 payload 对齐（见 docs 名人堂服务规划 §七），上报时可直接取数。
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "save" / "eval_cache"

_LOCK = threading.Lock()
_LOADED: dict[str, dict[str, Any]] = {}  # file_stem → {"gene_hash":…, "entries":{key: value}}


def gene_hash_of(variant: dict) -> str:
    """variant 的基因哈希：自带 hash 字段优先，否则 slots 排序后的 sha256。"""
    h = str(variant.get("hash") or "").strip()
    if h:
        return h
    slots = variant.get("slots") or {}
    canon = json.dumps(sorted(slots.items()), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _entry_key(model: str, case_ref: dict) -> str:
    return "|".join(
        str(x or "")
        for x in (
            model,
            case_ref.get("suite"),
            case_ref.get("id"),
            case_ref.get("level") or "basic",
        )
    )


def _file_for(gene_hash: str) -> Path:
    return CACHE_DIR / f"{gene_hash[:16]}.json"


def _load(gene_hash: str) -> dict[str, Any]:
    """读（并缓存）某 variant 的缓存文件。调用方须持锁。"""
    stem = gene_hash[:16]
    if stem in _LOADED:
        return _LOADED[stem]
    data: dict[str, Any] = {"gene_hash": gene_hash, "entries": {}}
    path = CACHE_DIR / f"{stem}.json"
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("entries"), dict):
                data = raw
        except (OSError, ValueError):
            pass
    _LOADED[stem] = data
    return data


def _stats_of(scores: list[float]) -> dict[str, Any]:
    from jobs import calc_stats

    return calc_stats([float(s) for s in scores])


def cache_get(gene_hash: str, model: str, case_ref: dict) -> dict | None:
    """命中返回 {scores, mean, sdv, n, updated_at}，未命中返回 None。"""
    if not gene_hash:
        return None
    with _LOCK:
        ent = _load(gene_hash)["entries"].get(_entry_key(model, case_ref))
        return dict(ent) if isinstance(ent, dict) else None


def cache_put(gene_hash: str, model: str, case_ref: dict, scores: list[float]) -> dict:
    """写入/合并某 (variant, model, case) 的鉴定分数，落盘后返回最新 entry。"""
    if not gene_hash or not scores:
        return {}
    key = _entry_key(model, case_ref)
    with _LOCK:
        data = _load(gene_hash)
        old = data["entries"].get(key) or {}
        merged = [float(s) for s in (old.get("scores") or [])] + [float(s) for s in scores]
        ent = {
            "scores": merged,
            **_stats_of(merged),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        data["entries"][key] = ent
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _file_for(gene_hash).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return dict(ent)


def cache_stats() -> dict[str, int]:
    """{entries, variants}：缓存条目总数与 variant 文件数。"""
    entries = 0
    variants = 0
    with _LOCK:
        if CACHE_DIR.is_dir():
            for path in CACHE_DIR.glob("*.json"):
                data = _load(path.stem)
                variants += 1
                entries += len(data.get("entries") or {})
        else:
            for data in _LOADED.values():
                variants += 1
                entries += len(data.get("entries") or {})
    return {"entries": entries, "variants": variants}
