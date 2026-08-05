"""Tests for factory preflight（起飞前检查）— no live LLM, no secrets access."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "factory" / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import preflight  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """key 来源全部截断（env 清空 + key 文件指向不存在路径），缓存目录指向 tmp。"""
    for name in preflight.KEY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(preflight, "KEY_FILES", (tmp_path / "no_such.key",))
    monkeypatch.setattr(preflight, "CACHE_DIR", tmp_path / "eval_cache")
    monkeypatch.delenv("YIAGENT_HOF_ENABLED", raising=False)


def _manifest(n_cases: int = 6, n_hold: int = 5) -> dict:
    return {
        "id": "m_pf",
        "demand": "d",
        "cases": [{"suite": "s", "id": f"c{i}", "level": "basic"} for i in range(n_cases)],
        "holdout": [
            {"suite": "s", "id": f"h{i}", "level": "basic"} for i in range(n_hold)
        ],
    }


def _patch_types(monkeypatch, types: list[str] | None):
    """让 resolve_cases 返回指定 test_type 轮转分布的假题。"""

    def fake_resolve(m, part="cases"):
        return [
            {**ref, "test_type": (types[i % len(types)] if types else None)}
            for i, ref in enumerate(m.get(part) or [])
        ]

    monkeypatch.setattr(preflight, "resolve_cases", fake_resolve)


_GOOD_PARAMS = {"max_tokens_budget": 100_000, "max_generations": 4, "eval_reps": 2}


# ---- key 可用性（正反例）----


def test_check_api_key_sources(monkeypatch, tmp_path):
    assert preflight.check_api_key()["ok"] is False  # 全部来源截断
    assert preflight.check_api_key(api_key="x" * 12) == {"ok": True, "source": "request"}
    monkeypatch.setenv("KIMI_API_KEY", "k")
    assert preflight.check_api_key()["source"] == "env:KIMI_API_KEY"
    monkeypatch.delenv("KIMI_API_KEY")
    key_file = tmp_path / "kimi_coding_plan.key"
    key_file.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(preflight, "KEY_FILES", (key_file,))
    got = preflight.check_api_key()
    assert got["ok"] is True and got["source"] == "file:kimi_coding_plan.key"
    # 只查存在性，不回显内容
    assert "dummy" not in json.dumps(got)


# ---- manifest / holdout / 题型分布 ----


def test_preflight_missing_manifest_is_error(monkeypatch):
    def boom(mid):
        raise KeyError(f"manifest not found: {mid}")

    monkeypatch.setattr(preflight, "load_manifest", boom)
    out = preflight.run_preflight(manifest_id="m_gone")
    assert out["ok"] is False
    assert any("manifest" in e for e in out["errors"])


def test_preflight_no_key_is_error(monkeypatch):
    _patch_types(monkeypatch, ["text"])
    out = preflight.run_preflight(manifest=_manifest(), params=_GOOD_PARAMS)
    assert out["ok"] is False
    assert any("API key" in e for e in out["errors"])


def test_preflight_holdout_count_warnings(monkeypatch):
    _patch_types(monkeypatch, ["text"])
    out0 = preflight.run_preflight(manifest=_manifest(n_hold=0), api_key="k" * 12, params=_GOOD_PARAMS)
    assert any("holdout 0 题" in w for w in out0["warnings"])
    out2 = preflight.run_preflight(manifest=_manifest(n_hold=2), api_key="k" * 12, params=_GOOD_PARAMS)
    assert any("<3" in w and "结论力弱" in w for w in out2["warnings"])
    out4 = preflight.run_preflight(manifest=_manifest(n_hold=4), api_key="k" * 12, params=_GOOD_PARAMS)
    assert any("<5" in w for w in out4["warnings"])
    out5 = preflight.run_preflight(manifest=_manifest(n_hold=5), api_key="k" * 12, params=_GOOD_PARAMS)
    assert not any("holdout" in w for w in out5["warnings"])


def test_preflight_mixed_types_warns_stratified(monkeypatch):
    _patch_types(monkeypatch, ["text", "image"])
    out = preflight.run_preflight(manifest=_manifest(), api_key="k" * 12, params=_GOOD_PARAMS)
    assert any("混题型" in w and "分层" in w for w in out["warnings"])
    assert out["checks"]["distribution"]["test_types"]  # 分布入 checks
    # 单一题型不报混题型
    _patch_types(monkeypatch, ["text"])
    out1 = preflight.run_preflight(manifest=_manifest(), api_key="k" * 12, params=_GOOD_PARAMS)
    assert not any("混题型" in w for w in out1["warnings"])


# ---- HOF / 缓存 / 预算 ----


def test_preflight_hof_budget_param_warnings(monkeypatch):
    _patch_types(monkeypatch, ["text"])
    out = preflight.run_preflight(manifest=_manifest(), api_key="k" * 12, params={})
    assert any("YIAGENT_HOF_ENABLED" in w for w in out["warnings"])
    assert any("max_tokens_budget" in w for w in out["warnings"])
    out2 = preflight.run_preflight(
        manifest=_manifest(),
        api_key="k" * 12,
        params={"max_tokens_budget": 1000, "max_generations": 1, "eval_reps": 1},
    )
    assert any("偏小" in w for w in out2["warnings"])
    assert any("max_generations" in w for w in out2["warnings"])
    assert any("eval_reps" in w for w in out2["warnings"])


def test_preflight_cache_not_writable_warns(monkeypatch, tmp_path):
    _patch_types(monkeypatch, ["text"])
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")  # 同名文件占路 → mkdir 失败
    monkeypatch.setattr(preflight, "CACHE_DIR", blocker)
    out = preflight.run_preflight(manifest=_manifest(), api_key="k" * 12, params=_GOOD_PARAMS)
    assert out["checks"]["eval_cache"]["writable"] is False
    assert any("缓存目录不可写" in w for w in out["warnings"])


def test_preflight_all_good(monkeypatch):
    _patch_types(monkeypatch, ["text"])
    monkeypatch.setenv("YIAGENT_HOF_ENABLED", "1")
    out = preflight.run_preflight(manifest=_manifest(), api_key="k" * 12, params=_GOOD_PARAMS)
    assert out["ok"] is True
    assert out["errors"] == []
    assert out["warnings"] == []
    assert out["checks"]["hof"]["enabled"] is True
    assert out["checks"]["manifest"]["holdout"] == 5
    json.dumps(out)  # 整体可 JSON 序列化


# ---- HTTP 路由（注册顺序：/api/evolve/preflight 不被 {run_id} 吃掉）----


def test_preflight_route(monkeypatch):
    import importlib.util

    from fastapi.testclient import TestClient

    # 裸 import app 会撞到 hof/server/app.py（同名模块先入 sys.modules），按路径加载
    spec = importlib.util.spec_from_file_location("factory_app", SERVER / "app.py")
    factory_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(factory_app)

    called: dict = {}

    def fake_run_preflight(**kw):
        called.update(kw)
        return {"ok": True, "errors": [], "warnings": ["w"], "checks": {}}

    monkeypatch.setattr(factory_app, "run_preflight", fake_run_preflight)
    with TestClient(factory_app.app) as c:
        resp = c.get("/api/evolve/preflight", params={"manifest_id": "m_pf"})
    assert resp.status_code == 200
    assert resp.json()["warnings"] == ["w"]
    assert called["manifest_id"] == "m_pf"
