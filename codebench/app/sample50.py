"""从 LiveCodeBench release_v5 全量分层抽样 50 题（public+private）。

优先读 HF 本地缓存 jsonl（免联网 streaming），避免 SSL/OOM。
"""
from __future__ import annotations

import base64
import json
import os
import pickle
import random
import zlib
from pathlib import Path
from typing import Any, Iterable

SEED = 202608092  # r2：全量分层 + public+private
N = 50
RELEASE = "release_v5"
QUOTA = {"easy": 20, "medium": 20, "hard": 10}
SAMPLE_TAG = "r2_public_private_stratified"

# 与 HF code_generation_lite.py ALLOWED_FILES 对齐
RELEASE_FILES = {
    "release_v5": ["test.jsonl", "test2.jsonl", "test3.jsonl", "test4.jsonl", "test5.jsonl"],
    "release_v6": [
        "test.jsonl",
        "test2.jsonl",
        "test3.jsonl",
        "test4.jsonl",
        "test5.jsonl",
        "test6.jsonl",
    ],
}


def _hf_snapshot_dir() -> Path | None:
    home = Path(os.environ.get("HF_HOME", "/data/hf"))
    snap_root = home / "hub" / "datasets--livecodebench--code_generation_lite" / "snapshots"
    if not snap_root.is_dir():
        return None
    snaps = sorted([p for p in snap_root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    return snaps[0] if snaps else None


def _iter_local_rows(release: str) -> Iterable[dict]:
    snap = _hf_snapshot_dir()
    if snap is None:
        raise FileNotFoundError("hf_snapshot_missing")
    files = RELEASE_FILES.get(release) or RELEASE_FILES["release_v5"]
    for name in files:
        path = snap / name
        if not path.exists():
            raise FileNotFoundError(f"missing_shard:{path}")
        print(f"  reading {path.name}…", flush=True)
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def _decode_tests(raw: Any) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [t for t in raw if isinstance(t, dict)]
    if not isinstance(raw, str):
        return []
    try:
        data = json.loads(raw)
    except Exception:
        data = json.loads(
            pickle.loads(zlib.decompress(base64.b64decode(raw.encode("utf-8"))))
        )
    if not isinstance(data, list):
        return []
    return [t for t in data if isinstance(t, dict)]


def _parse_meta(meta: Any) -> dict:
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        try:
            m = json.loads(meta)
            return m if isinstance(m, dict) else {}
        except Exception:
            return {}
    return {}


def _materialize(row: dict) -> dict:
    meta = _parse_meta(row.get("metadata"))
    public = _decode_tests(row.get("public_test_cases"))
    private = _decode_tests(row.get("private_test_cases"))
    tests = public + private
    return {
        "question_id": row.get("question_id"),
        "question_title": row.get("question_title"),
        "platform": str(row.get("platform") or ""),
        "difficulty": str(row.get("difficulty") or "").lower(),
        "contest_date": str(row.get("contest_date") or ""),
        "starter_code": row.get("starter_code") or "",
        "question_content": row.get("question_content") or "",
        "metadata": meta,
        "input_output": {
            "inputs": [t.get("input", "") for t in tests],
            "outputs": [t.get("output", "") for t in tests],
            "fn_name": meta.get("func_name"),
        },
        "n_public_tests": len(public),
        "n_private_tests": len(private),
    }


def build_sample(out_path: Path, *, n: int = N, seed: int = SEED, release: str = RELEASE) -> dict[str, Any]:
    print(f"pass1: index local shards ({release})…", flush=True)
    index: list[dict[str, str]] = []
    for i, row in enumerate(_iter_local_rows(release)):
        d = str(row.get("difficulty", "")).lower()
        if d not in QUOTA:
            continue
        qid = str(row.get("question_id") or "")
        if not qid:
            continue
        index.append({"question_id": qid, "difficulty": d})
        if (i + 1) % 200 == 0:
            print(f"  indexed={len(index)}", flush=True)
    print(f"pass1 done: {len(index)} problems", flush=True)

    buckets: dict[str, list[str]] = {"easy": [], "medium": [], "hard": []}
    for item in index:
        buckets[item["difficulty"]].append(item["question_id"])

    rng = random.Random(seed)
    picked: list[str] = []
    for diff, want in QUOTA.items():
        pool = list(dict.fromkeys(buckets.get(diff, [])))
        rng.shuffle(pool)
        take = pool[:want]
        picked.extend(take)
        print(f"  pick {diff}: {len(take)}/{want} (pool={len(pool)})", flush=True)
    picked_set = set(picked[:n])

    print(f"pass2: materialize {len(picked_set)} with public+private…", flush=True)
    by_id: dict[str, dict] = {}
    for row in _iter_local_rows(release):
        qid = str(row.get("question_id") or "")
        if qid not in picked_set or qid in by_id:
            continue
        by_id[qid] = _materialize(row)
        print(f"  …{len(by_id)}/{len(picked_set)} qid={qid}", flush=True)
        if len(by_id) >= len(picked_set):
            break

    rows = [by_id[qid] for qid in picked if qid in by_id][:n]
    if len(rows) < n:
        raise RuntimeError(f"materialize_shortfall:{len(rows)}/{n}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_pub = sum(int(r.get("n_public_tests") or 0) for r in rows)
    n_priv = sum(int(r.get("n_private_tests") or 0) for r in rows)
    dates = sorted(r.get("contest_date") or "" for r in rows)
    meta = {
        "seed": seed,
        "n": len(rows),
        "release": release,
        "quota": QUOTA,
        "tests": "public_and_private",
        "sample_tag": SAMPLE_TAG,
        "source": "local_hf_jsonl",
        "index_size": len(index),
        "counts": {
            d: sum(1 for r in rows if r["difficulty"] == d) for d in ("easy", "medium", "hard")
        },
        "n_public_tests_total": n_pub,
        "n_private_tests_total": n_priv,
        "contest_date_min": dates[0] if dates else None,
        "contest_date_max": dates[-1] if dates else None,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "problems": rows}, f, ensure_ascii=False)
    print("wrote", out_path, "bytes", out_path.stat().st_size, flush=True)
    return meta


def load_sample(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
