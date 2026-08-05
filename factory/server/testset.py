"""测试集 manifest：从用例库确定性抽样进化集 + 分层 holdout。

进化集参与多代进化鉴定；holdout 集只做终验，不参与进化。
筛选 / 抽样 / 分层均为纯函数，可单测。
"""

from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path
from typing import Any

from case_library import LIBRARY

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "save" / "manifests"

SCHEMA = "yiagent.factory.testset"
VERSION = 1


def filter_items(
    items: list[dict],
    *,
    suites: list[str] | None = None,
    dimensions: list[str] | None = None,
    q: str | None = None,
    ids: list[str] | None = None,
    level: str = "basic",
) -> list[dict]:
    """纯过滤：suites/dimensions/q/ids/level 可用性。items 为 LIBRARY.list_cases 的目录行。"""
    suite_set = {s.strip() for s in (suites or []) if s and s.strip()}
    dim_set = {d.strip() for d in (dimensions or []) if d and d.strip()}
    qn = (q or "").strip().lower()
    id_set = {i.strip() for i in (ids or []) if i and i.strip()}
    lv = (level or "basic").strip().lower()
    out: list[dict] = []
    for it in items:
        key = f"{it.get('suite')}/{it.get('id')}"
        if id_set and key not in id_set and str(it.get("id")) not in id_set:
            continue
        if suite_set and it.get("suite") not in suite_set:
            continue
        if dim_set and it.get("dimension") not in dim_set:
            continue
        if qn:
            blob = f"{it.get('id')} {it.get('title')} {it.get('description')} {it.get('dimension')}".lower()
            if qn not in blob:
                continue
        if lv and lv not in (it.get("levels") or []):
            continue
        out.append(it)
    return out


def sample_cases(candidates: list[dict], size: int, rng: random.Random) -> list[dict]:
    """确定性抽样 size 题（同 seed 同结果）。"""
    n = min(max(0, int(size)), len(candidates))
    if n <= 0:
        return []
    return rng.sample(list(candidates), n)


def stratified_holdout(
    remaining: list[dict], n: int, rng: random.Random
) -> list[dict]:
    """按 suite 分层抽 n 题 holdout（比例配额 + 最大余数法）。"""
    n = min(max(0, int(n)), len(remaining))
    if n <= 0:
        return []
    by_suite: dict[str, list[dict]] = {}
    for it in remaining:
        by_suite.setdefault(str(it.get("suite") or ""), []).append(it)
    total = len(remaining)
    # 配额：floor + 最大余数补齐
    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    assigned = 0
    for suite, rows in by_suite.items():
        exact = n * len(rows) / total
        q_floor = int(exact)
        quotas[suite] = min(q_floor, len(rows))
        assigned += quotas[suite]
        remainders.append((exact - q_floor, suite))
    for _, suite in sorted(remainders, key=lambda x: (-x[0], x[1])):
        if assigned >= n:
            break
        if quotas[suite] < len(by_suite[suite]):
            quotas[suite] += 1
            assigned += 1
    out: list[dict] = []
    for suite in sorted(by_suite):
        take = quotas.get(suite, 0)
        if take > 0:
            out.extend(rng.sample(by_suite[suite], take))
    return out


def _gather_candidates() -> list[dict]:
    """分页拉全量题目录（list_cases 单页上限 200）。"""
    items: list[dict] = []
    offset = 0
    while True:
        page = LIBRARY.list_cases(limit=200, offset=offset)
        items.extend(page.get("items") or [])
        total = int(page.get("total") or 0)
        offset += 200
        if offset >= total or not page.get("items"):
            break
    return items


def build_manifest(
    demand: str,
    *,
    suites: list[str] | None = None,
    dimensions: list[str] | None = None,
    q: str | None = None,
    level: str = "basic",
    size: int = 10,
    seed: int = 42,
    holdout_ratio: float = 0.2,
    ids: list[str] | None = None,
) -> dict[str, Any]:
    """建测试集 manifest：进化集 + 分层 holdout（确定性，同 seed 可复现）。"""
    demand = (demand or "").strip()
    if not demand:
        raise ValueError("demand required")
    candidates = filter_items(
        _gather_candidates(),
        suites=suites,
        dimensions=dimensions,
        q=q,
        ids=ids,
        level=level,
    )
    if not candidates:
        raise ValueError("no cases match the given filters")
    rng = random.Random(int(seed))
    evo_items = sample_cases(candidates, int(size), rng)
    evo_keys = {(it["suite"], it["id"]) for it in evo_items}
    remaining = [it for it in candidates if (it["suite"], it["id"]) not in evo_keys]
    ratio = max(0.0, min(float(holdout_ratio), 1.0))
    hold_n = 0
    if remaining and ratio > 0:
        hold_n = min(len(remaining), max(1, round(len(evo_items) * ratio)))
    hold_items = stratified_holdout(remaining, hold_n, rng) if hold_n else []
    lv = (level or "basic").strip().lower()
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "id": uuid.uuid4().hex[:12],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "demand": demand,
        "params": {
            "suites": list(suites or []),
            "dimensions": list(dimensions or []),
            "q": q,
            "level": lv,
            "size": int(size),
            "seed": int(seed),
            "holdout_ratio": float(holdout_ratio),
            "ids": list(ids or []),
            "pool_size": len(candidates),
        },
        "cases": [
            {"suite": it["suite"], "id": it["id"], "level": lv} for it in evo_items
        ],
        "holdout": [
            {"suite": it["suite"], "id": it["id"], "level": lv} for it in hold_items
        ],
    }


def save_manifest(manifest: dict) -> Path:
    """持久化到 save/manifests/{id}.json。"""
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    path = MANIFEST_DIR / f"{manifest['id']}.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_manifest(manifest_id: str) -> dict[str, Any]:
    path = MANIFEST_DIR / f"{(manifest_id or '').strip()}.json"
    if not path.is_file():
        raise KeyError(f"manifest not found: {manifest_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"bad manifest schema: {data.get('schema')}")
    return data


def resolve_cases(manifest: dict, part: str = "cases") -> list[dict[str, Any]]:
    """把 manifest 里的 {suite,id,level} 展开成完整题（带各自 criteria）。

    to_factory_case 不带 test_type；此处从原始题目录回填，供 preflight 题型分布
    与评分卡分层均分按真实题型归类（缺省回落 dimension 会误报混题型）。
    """
    out: list[dict[str, Any]] = []
    for ref in manifest.get(part) or []:
        case = LIBRARY.to_factory_case(ref["suite"], ref["id"], ref.get("level") or "basic")
        if not case.get("test_type"):
            raw_type = str(
                LIBRARY.get_raw(ref["suite"], ref["id"]).get("test_type") or ""
            ).strip()
            if raw_type:
                case["test_type"] = raw_type
        out.append(case)
    return out
