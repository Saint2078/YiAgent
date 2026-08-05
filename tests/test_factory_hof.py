"""Tests for factory Hall-of-Fame client: eval_cache + hof_ship (no live LLM / network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "factory" / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import eval_cache  # noqa: E402
import evolve  # noqa: E402
import hof_ship  # noqa: E402


@pytest.fixture()
def cache_dir(tmp_path, monkeypatch):
    d = tmp_path / "eval_cache"
    monkeypatch.setattr(eval_cache, "CACHE_DIR", d)
    eval_cache._LOADED.clear()
    yield d
    eval_cache._LOADED.clear()


def _case(cid: str = "l_001") -> dict:
    return {
        "suite": "xsct-l",
        "id": cid,
        "level": "basic",
        "messages": [{"role": "user", "content": "题面"}],
    }


def _variant(vid: str = "var.a", h: str = "hash-a") -> dict:
    return {
        "id": vid,
        "hash": h,
        "title": f"title {vid}",
        "slots": {s: f"{s.lower()}.a" for s in ("G1", "G2", "G3", "G4", "G5")},
    }


# ---- eval_cache ----


def test_gene_hash_prefers_variant_hash_and_stable():
    assert eval_cache.gene_hash_of(_variant(h="yg-x-abc")) == "yg-x-abc"
    v = _variant()
    del v["hash"]
    h1 = eval_cache.gene_hash_of(v)
    # slots 顺序不影响哈希
    v2 = {"id": "var.x", "slots": dict(reversed(list(v["slots"].items())))}
    assert eval_cache.gene_hash_of(v2) == h1
    # slots 不同 → 哈希不同
    v3 = {"id": "var.y", "slots": {**v["slots"], "G5": "g5.b"}}
    assert eval_cache.gene_hash_of(v3) != h1


def test_cache_put_get_roundtrip_and_merge(cache_dir):
    gh = "hash-a"
    case = _case()
    assert eval_cache.cache_get(gh, "k3", case) is None
    ent = eval_cache.cache_put(gh, "k3", case, [80.0, 82.0])
    assert ent["n"] == 2 and ent["mean"] == 81.0
    got = eval_cache.cache_get(gh, "k3", case)
    assert got["scores"] == [80.0, 82.0]
    # 再 put 合并而非覆盖
    eval_cache.cache_put(gh, "k3", case, [84.0])
    assert eval_cache.cache_get(gh, "k3", case)["scores"] == [80.0, 82.0, 84.0]
    # key 含 model / level：不同 model 不命中
    assert eval_cache.cache_get(gh, "other-model", case) is None
    # 分文件落盘：文件名 = gene_hash[:16]
    assert (cache_dir / f"{gh[:16]}.json").is_file()


def test_cache_stats(cache_dir):
    case = _case()
    eval_cache.cache_put("hash-a", "k3", case, [80.0])
    eval_cache.cache_put("hash-a", "k3", _case("l_002"), [81.0])
    eval_cache.cache_put("hash-b", "k3", case, [70.0])
    stats = eval_cache.cache_stats()
    assert stats == {"entries": 3, "variants": 2}


# ---- evolve 缓存接线（mock LLM） ----


def _run(eval_reps: int = 2, use_cache: bool = True) -> evolve.EvolveRun:
    return evolve.EvolveRun(
        id="testrun01",
        model="k3",
        params={"eval_reps": eval_reps, "workers": 2, "use_cache": use_cache},
    )


def _mock_eval(monkeypatch, score: float = 88.0) -> list[dict]:
    calls: list[dict] = []

    def fake(**kw):
        calls.append(kw)
        return {
            "variant_id": str(kw["variant"]["id"]),
            "rep": kw["rep"],
            "score": score,
            "ok": True,
            "dimension_scores": {"指令遵循": score},
        }

    monkeypatch.setattr(evolve, "_eval_one_variant", fake)
    return calls


def test_evolve_cache_full_hit_skips_llm(cache_dir, tmp_path, monkeypatch):
    bank = {"alleles": {}, "variants": [_variant()]}
    case = _case()
    eval_cache.cache_put("hash-a", "k3", case, [80.0, 82.0])
    calls = _mock_eval(monkeypatch)
    mgr = evolve.EvolveManager()
    cards = mgr._evaluate_generation(_run(), "key", bank, [case], 0, tmp_path)
    assert calls == []  # 全部命中，零 LLM 调用
    assert cards[0]["cases"][0]["scores"] == [80.0, 82.0]
    assert cards[0]["mean"] == 81.0


def test_evolve_cache_miss_runs_and_writes_back(cache_dir, tmp_path, monkeypatch):
    bank = {"alleles": {}, "variants": [_variant()]}
    case = _case()
    calls = _mock_eval(monkeypatch, score=90.0)
    mgr = evolve.EvolveManager()
    cards = mgr._evaluate_generation(_run(), "key", bank, [case], 0, tmp_path)
    assert len(calls) == 2  # 未命中：跑满 reps
    assert cards[0]["cases"][0]["scores"] == [90.0, 90.0]
    ent = eval_cache.cache_get("hash-a", "k3", case)
    assert ent["scores"] == [90.0, 90.0]  # 跑完写回缓存


def test_evolve_cache_partial_hit_runs_delta(cache_dir, tmp_path, monkeypatch):
    bank = {"alleles": {}, "variants": [_variant()]}
    case = _case()
    eval_cache.cache_put("hash-a", "k3", case, [80.0])  # 只有 1 个 rep
    calls = _mock_eval(monkeypatch, score=90.0)
    mgr = evolve.EvolveManager()
    cards = mgr._evaluate_generation(_run(eval_reps=2), "key", bank, [case], 0, tmp_path)
    assert len(calls) == 1  # 只补跑差额
    assert cards[0]["cases"][0]["scores"] == [80.0, 90.0]
    ent = eval_cache.cache_get("hash-a", "k3", case)
    assert ent["scores"] == [80.0, 90.0]  # 合并写回
    assert ent["n"] == 2


def test_evolve_use_cache_off_ignores_cache(cache_dir, tmp_path, monkeypatch):
    bank = {"alleles": {}, "variants": [_variant()]}
    case = _case()
    eval_cache.cache_put("hash-a", "k3", case, [80.0, 82.0])
    calls = _mock_eval(monkeypatch, score=90.0)
    mgr = evolve.EvolveManager()
    cards = mgr._evaluate_generation(
        _run(use_cache=False), "key", bank, [case], 0, tmp_path
    )
    assert len(calls) == 2  # 关闭缓存：照跑
    assert cards[0]["cases"][0]["scores"] == [90.0, 90.0]


# ---- hof_ship：build_submissions / redact ----


def _scorecard(vid: str, h: str | None, mean: float) -> dict:
    card = {
        "run_id": "run123",
        "gen": 0,
        "variant_id": vid,
        "title": f"title {vid}",
        "hash": h,
        "slots": {s: f"{s.lower()}.a" for s in ("G1", "G2", "G3", "G4", "G5")},
        "reps": 2,
        "cases": [
            {
                "suite": "xsct-l",
                "id": "l_001",
                "level": "basic",
                "scores": [mean, mean],
                "stats": {"n": 2, "mean": mean, "sdv": 0.0},
                "dimension_scores": {"指令遵循": mean, "表达清晰": mean - 2},
            }
        ],
        "n": 2,
        "mean": mean,
        "sdv": 0.0,
        "composite": mean,
    }
    return card


@pytest.fixture()
def run_dir(tmp_path) -> Path:
    rd = tmp_path / "run123"
    bank = {
        "alleles": {"G1": [{"id": "g1.a", "label": "a", "text": "等位文本"}]},
        "variants": [_variant("var.a", "hash-a")],
    }
    report = {
        "schema": "yiagent.factory.evolve_report",
        "run_id": "run123",
        "model": "k3",
        "demand": "用户需求全文不应上报",
        "champion": {
            "gen": 1,
            "variant_id": "var.b",
            "composite": 90.0,
            "variant": {"id": "var.b", "hash": "hash-b"},
            "bank": bank,
        },
        "champion_curve": [
            {"gen": 0, "variant_id": "var.a", "composite": 85.0},
            {"gen": 1, "variant_id": "var.b", "composite": 90.0},
        ],
    }
    (rd / "gen0").mkdir(parents=True)
    (rd / "gen1").mkdir(parents=True)
    (rd / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (rd / "gen0" / "scorecard_var.a.json").write_text(
        json.dumps(_scorecard("var.a", "hash-a", 85.0)), encoding="utf-8"
    )
    (rd / "gen1" / "scorecard_var.b.json").write_text(
        json.dumps(_scorecard("var.b", "hash-b", 90.0)), encoding="utf-8"
    )
    return rd


def test_build_submissions_schema(run_dir):
    subs = hof_ship.build_submissions(run_dir, contributor_id="anon_test")
    # 跨代总冠军 + 各代冠军；总冠军与 gen1 冠军同 variant → gene_hash 去重后 2 份
    assert len(subs) == 2
    by_gen = {s["context"]["evolve"]["generation"]: s for s in subs}
    overall = by_gen[1]
    assert overall["schema"] == "yiagent.hof.submission"
    assert overall["version"] == "0.1"
    assert overall["contributor_id"] == "anon_test"
    assert overall["genome"]["gene_hash"] == "hash-b"
    assert overall["genome"]["variant_id"] == "var.b"
    assert overall["genome"]["bank"]["alleles"]["G1"][0]["text"] == "等位文本"
    ev = overall["evaluation"]
    assert ev["model"] == "k3"
    assert ev["reps"] == 2
    assert ev["stats"] == {"mean": 90.0, "sdv": 0.0, "composite": 90.0, "n": 2}
    # testset 只传公共题引用，无题面内容
    assert ev["testset"] == {
        "kind": "xsct",
        "cases": [{"suite": "xsct-l", "id": "l_001", "level": "basic"}],
    }
    assert ev["per_case"] == [{"suite": "xsct-l", "id": "l_001", "mean": 90.0, "sdv": 0.0}]
    assert ev["dim_means"] == {"指令遵循": 90.0, "表达清晰": 88.0}
    ctx = overall["context"]
    assert ctx["yiagent_version"] == hof_ship.DEFAULT_YIAGENT_VERSION
    assert ctx["evolve"]["run_id_hash"] != "run123"  # 只传哈希
    assert sorted(ctx["demand_tags"]) == ["指令遵循", "表达清晰"]
    # 总冠军优先占位 gene_hash，gen0 冠军仍各报一份
    assert by_gen[0]["genome"]["gene_hash"] == "hash-a"


def test_redact_whitelist_drops_undeclared(run_dir):
    subs = hof_ship.build_submissions(run_dir, contributor_id="anon_test")
    dirty = dict(subs[0])
    dirty["api_key"] = "sk-secret-123456"
    dirty["local_path"] = "/Users/caelum/secret/run123"
    dirty["genome"] = {**dirty["genome"], "api_key": "sk-secret-123456"}
    dirty["evaluation"] = {
        **dirty["evaluation"],
        "preview": "模型输出全文",
        "messages": [{"role": "user", "content": "题面全文"}],
    }
    dirty["context"] = {**dirty["context"], "demand": "用户需求全文"}
    clean = hof_ship.redact(dirty)
    blob = json.dumps(clean, ensure_ascii=False)
    assert "sk-secret" not in blob
    assert "/Users/caelum" not in blob
    assert "模型输出全文" not in blob
    assert "题面全文" not in blob
    assert "用户需求全文" not in blob
    # 白名单字段保留
    assert clean["schema"] == "yiagent.hof.submission"
    assert clean["genome"]["gene_hash"] == "hash-b"
    assert clean["evaluation"]["stats"]["mean"] == 90.0
    assert set(clean["evaluation"].keys()) == {
        "model",
        "testset",
        "reps",
        "stats",
        "per_case",
        "dim_means",
    }


def test_dry_run_no_network(run_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(hof_ship, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(hof_ship, "IDENTITY_FILE", tmp_path / "hof_identity.json")

    def boom(*a, **kw):
        raise AssertionError("dry_run must not touch network")

    monkeypatch.setattr(hof_ship, "_post_json", boom)
    subs = hof_ship.dry_run(run_dir)
    assert len(subs) == 2
    assert all(s["schema"] == "yiagent.hof.submission" for s in subs)


# ---- hof_ship：队列 / flush / contributor_id ----


def test_ship_batch_and_failure_queue(tmp_path, monkeypatch):
    qdir = tmp_path / "ship_queue"
    monkeypatch.setattr(hof_ship, "QUEUE_DIR", qdir)
    payload = {"schema": "yiagent.hof.submission", "contributor_id": "anon_t"}
    sent: list[dict] = []

    monkeypatch.setattr(
        hof_ship, "_post_json", lambda url, body, timeout: sent.append((url, body)) or {"ok": 1}
    )
    res = hof_ship.ship([payload], base_url="http://localhost:8788")
    assert res["ok"] and res["submitted"] == 1
    url, body = sent[0]
    assert url == "http://localhost:8788/api/hof/submit"
    assert body["schema"] == "yiagent.hof.batch"
    assert body["submissions"] == [payload]
    assert hof_ship.queue_size() == 0

    def raise_err(url, body, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(hof_ship, "_post_json", raise_err)
    res = hof_ship.ship([payload], base_url="http://localhost:8788")
    assert not res["ok"] and res["submitted"] == 0
    assert hof_ship.queue_size() == 1
    queued = json.loads(next(qdir.glob("*.json")).read_text(encoding="utf-8"))
    assert queued["payloads"] == [payload]


def test_flush_queue(tmp_path, monkeypatch):
    qdir = tmp_path / "ship_queue"
    qdir.mkdir()
    monkeypatch.setattr(hof_ship, "QUEUE_DIR", qdir)
    item = {"url": "http://x/api/hof/submit", "payloads": [{"schema": "s"}]}
    (qdir / "a.json").write_text(json.dumps(item), encoding="utf-8")
    (qdir / "b.json").write_text(json.dumps(item), encoding="utf-8")

    monkeypatch.setattr(hof_ship, "_post_json", lambda url, body, timeout: {"ok": 1})
    out = hof_ship.flush_queue()
    assert out == {"sent": 2, "failed": 0, "remaining": 0}
    assert list(qdir.glob("*.json")) == []

    (qdir / "c.json").write_text(json.dumps(item), encoding="utf-8")

    def raise_err(url, body, timeout):
        raise OSError("down")

    monkeypatch.setattr(hof_ship, "_post_json", raise_err)
    out = hof_ship.flush_queue()
    assert out["failed"] == 1 and out["remaining"] == 1


def test_contributor_id_persist_and_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(hof_ship, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(hof_ship, "IDENTITY_FILE", tmp_path / "hof_identity.json")
    c1 = hof_ship.contributor_id()
    assert c1.startswith("anon_")
    assert hof_ship.contributor_id() == c1  # 持久化后稳定
    (tmp_path / "hof_identity.json").unlink()  # 删文件重置
    c2 = hof_ship.contributor_id()
    assert c2.startswith("anon_") and c2 != c1


def test_enabled_default_off_and_status(tmp_path, monkeypatch):
    monkeypatch.delenv("YIAGENT_HOF_ENABLED", raising=False)
    monkeypatch.delenv("YIAGENT_HOF_URL", raising=False)
    monkeypatch.setattr(hof_ship, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(hof_ship, "IDENTITY_FILE", tmp_path / "hof_identity.json")
    monkeypatch.setattr(hof_ship, "QUEUE_DIR", tmp_path / "ship_queue")
    assert hof_ship.enabled() is False
    assert hof_ship.base_url() == "http://localhost:8788"
    st = hof_ship.status()
    assert st["enabled"] is False
    assert st["contributor_id"].startswith("anon_")
    assert st["queue_size"] == 0
    assert set(st["cache"].keys()) == {"entries", "variants"}
    monkeypatch.setenv("YIAGENT_HOF_ENABLED", "true")
    monkeypatch.setenv("YIAGENT_HOF_URL", "https://hof.example/")
    assert hof_ship.enabled() is True
    assert hof_ship.base_url() == "https://hof.example"
