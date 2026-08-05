"""起飞前检查：evolve 实跑前的题库 / 密钥 / HOF / 缓存 / 预算体检。

产出 {ok, errors, warnings, checks}：硬失败（manifest 缺失、无 API key）进 errors，
其余一律降级为 warnings——保守默认只警告不阻断启动（阻断口径见 docs/experiments.md）。
全程不发网络、不读密钥内容（只查存在性），可安全在实跑前随时调用。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import hof_ship
from eval_cache import CACHE_DIR
from testset import load_manifest, resolve_cases

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

# API key 来源约定：环境变量之一，或纯 key 文件（只查存在性，不读内容）
KEY_ENV_VARS = ("YIAGENT_API_KEY", "KIMI_API_KEY", "MOONSHOT_API_KEY")
KEY_FILES = (REPO_ROOT / "secrets" / "kimi_coding_plan.key",)


def check_api_key(api_key: str | None = None) -> dict[str, Any]:
    """key 可用性：请求自带 > 环境变量 > secrets key 文件；只报来源不报内容。"""
    if (api_key or "").strip():
        return {"ok": True, "source": "request"}
    for name in KEY_ENV_VARS:
        if (os.environ.get(name) or "").strip():
            return {"ok": True, "source": f"env:{name}"}
    for path in KEY_FILES:
        if path.is_file():
            return {"ok": True, "source": f"file:{path.name}"}
    return {"ok": False, "source": None}


def _type_dist(manifest: dict) -> dict[str, Any]:
    """题库/题型分布：cases+holdout 展开后按 test_type/dimension/suite 统计。"""
    refs = list(manifest.get("cases") or []) + list(manifest.get("holdout") or [])
    full = resolve_cases({"cases": refs}, "cases")
    types: dict[str, int] = {}
    suites: dict[str, int] = {}
    for c in full:
        t = str(c.get("test_type") or c.get("dimension") or "")
        if t:
            types[t] = types.get(t, 0) + 1
        s = str(c.get("suite") or "")
        if s:
            suites[s] = suites.get(s, 0) + 1
    return {"test_types": types, "suites": suites}


def run_preflight(
    *,
    manifest_id: str | None = None,
    manifest: dict | None = None,
    api_key: str | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """起飞前体检。errors 为硬失败，warnings 为建议项；ok = 无 errors。"""
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    # 1. manifest 存在性 + holdout 题数 + 题型分布
    m = manifest
    if m is None and manifest_id:
        try:
            m = load_manifest(manifest_id)
        except (KeyError, ValueError, OSError) as e:
            errors.append(f"manifest 缺失或损坏（{manifest_id}）：{e}")
    if m is None and not errors:
        errors.append("manifest 缺失：给 manifest_id 或内联 manifest 后才能起飞")
    if m is not None:
        n_cases = len(m.get("cases") or [])
        n_hold = len(m.get("holdout") or [])
        checks["manifest"] = {
            "id": m.get("id"),
            "cases": n_cases,
            "holdout": n_hold,
        }
        if not n_cases:
            errors.append("manifest.cases 为空：无进化题，跑不起来")
        if n_hold == 0:
            warnings.append("holdout 0 题：终验将整体跳过，report 无 holdout 结论")
        elif n_hold < 3:
            warnings.append(
                f"holdout 仅 {n_hold} 题（<3）：终验结论力弱（冒烟教训 n=2 不可下结论），"
                "正式跑建议 3–5 题"
            )
        elif n_hold < 5:
            warnings.append(f"holdout {n_hold} 题（<5）：可用，建议 5 题以增强终验结论")
        try:
            dist = _type_dist(m)
            checks["distribution"] = dist
            if len(dist["test_types"]) > 1:
                warnings.append(
                    f"题库混题型 {sorted(dist['test_types'])}：均分会被题间方差污染，"
                    "结论须按 T1 分层口径（report.champion_stratified）逐层解读，勿只看 composite"
                )
            if len(dist["suites"]) > 1:
                warnings.append(
                    f"题库跨套件 {sorted(dist['suites'])}：注意套件间难度差，"
                    "解读时对照 champion_stratified 分层均分"
                )
        except Exception as e:  # noqa: BLE001
            warnings.append(f"题库展开失败，无法检查题型分布：{e}")

    # 2. API key 可用性（只查存在性）
    key = check_api_key(api_key)
    checks["api_key"] = key
    if not key["ok"]:
        errors.append(
            "无可用 API key：请求带 api_key，或设环境变量 "
            f"{'/'.join(KEY_ENV_VARS)}，或放置 {KEY_FILES[0].name} key 文件"
        )

    # 3. 名人堂上报状态（严格 opt-in，未开启仅提示）
    checks["hof"] = {"enabled": hof_ship.enabled(), "url": hof_ship.base_url()}
    if not checks["hof"]["enabled"]:
        warnings.append(
            "YIAGENT_HOF_ENABLED 未开启：run 结束后不会自动上报名人堂"
            "（正式跑建议 YIAGENT_HOF_ENABLED=1）"
        )

    # 4. eval 缓存目录可写
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        probe = CACHE_DIR / ".preflight_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks["eval_cache"] = {"dir": str(CACHE_DIR), "writable": True}
    except OSError as e:
        checks["eval_cache"] = {"dir": str(CACHE_DIR), "writable": False}
        warnings.append(f"eval 缓存目录不可写（{CACHE_DIR}）：use_cache 将失效：{e}")

    # 5. 预算与参数合理性
    p = params or {}
    budget = p.get("max_tokens_budget")
    if not budget:
        warnings.append("未设 max_tokens_budget：失控时无预算护栏，正式跑建议设预算")
    elif int(budget) < 50_000:
        warnings.append(f"max_tokens_budget={budget} 偏小：可能过早触发 budget stop")
    if int(p.get("max_generations") or 0) < 2:
        warnings.append("max_generations<2：无代际比较，配对显著性门禁不会触发")
    if int(p.get("eval_reps") or 0) < 2:
        warnings.append("eval_reps<2：单 rep 方差大，正式跑建议 eval_reps≥2")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "checks": checks}
