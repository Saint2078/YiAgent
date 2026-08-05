"""Tests for factory testset manifest + evolve pure functions (no live LLM)."""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "factory" / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import evolve  # noqa: E402
import testset  # noqa: E402
from evolve import (  # noqa: E402
    attribute_failure,
    composite,
    crossover,
    gate_verdict,
    paired_gate,
    random_immigrant,
    select_elites,
    stratify_scores,
    summarize_failures,
    wall_by_stage,
)


def _fake_catalog(n_per_suite: int = 6) -> list[dict]:
    items = []
    for suite, dim in (("suite_a", "crit"), ("suite_b", "crit"), ("suite_c", "math")):
        for i in range(n_per_suite):
            items.append(
                {
                    "id": f"{suite}_{i:03d}",
                    "suite": suite,
                    "title": f"{suite} 第{i}题 推理",
                    "description": f"{dim} 维度题 {i}",
                    "dimension": dim,
                    "test_type": suite,
                    "levels": ["basic", "medium"],
                }
            )
    return items


@pytest.fixture()
def catalog(monkeypatch):
    items = _fake_catalog()
    monkeypatch.setattr(testset, "_gather_candidates", lambda: items)
    return items


# ---- manifest ----


def test_filter_items(catalog):
    by_suite = testset.filter_items(catalog, suites=["suite_a"])
    assert {it["suite"] for it in by_suite} == {"suite_a"}
    by_dim = testset.filter_items(catalog, dimensions=["math"])
    assert {it["dimension"] for it in by_dim} == {"math"}
    by_q = testset.filter_items(catalog, q="第1题")
    assert by_q and all("第1题" in it["title"] for it in by_q)
    by_ids = testset.filter_items(catalog, ids=["suite_a/suite_a_001", "suite_b_002"])
    assert {(it["suite"], it["id"]) for it in by_ids} == {
        ("suite_a", "suite_a_001"),
        ("suite_b", "suite_b_002"),
    }
    by_level = testset.filter_items(catalog, level="hard")
    assert by_level == []


def test_manifest_deterministic_same_seed(catalog):
    m1 = testset.build_manifest("需求", size=9, seed=7, holdout_ratio=0.2)
    m2 = testset.build_manifest("需求", size=9, seed=7, holdout_ratio=0.2)
    assert m1["cases"] == m2["cases"]
    assert m1["holdout"] == m2["holdout"]
    m3 = testset.build_manifest("需求", size=9, seed=8, holdout_ratio=0.2)
    assert m1["cases"] != m3["cases"]


def test_manifest_holdout_disjoint_and_stratified(catalog):
    m = testset.build_manifest("需求", size=9, seed=42, holdout_ratio=0.34)
    evo = {(c["suite"], c["id"]) for c in m["cases"]}
    hold = {(c["suite"], c["id"]) for c in m["holdout"]}
    assert len(evo) == 9
    assert evo.isdisjoint(hold)
    assert len(hold) >= 1  # 总量允许时至少留 1 题
    # 分层：holdout 覆盖多个 suite（catalog 有 3 个 suite）
    assert len({s for s, _ in hold}) >= 2


def test_manifest_pool_smaller_than_size(catalog, monkeypatch):
    small = _fake_catalog(2)[:4]
    monkeypatch.setattr(testset, "_gather_candidates", lambda: small)
    m = testset.build_manifest("需求", size=10, seed=1, holdout_ratio=0.5)
    assert len(m["cases"]) + len(m["holdout"]) == 4
    assert len(m["cases"]) == 4  # 进化集先吃满
    assert m["holdout"] == []


def test_manifest_empty_pool_raises(monkeypatch):
    monkeypatch.setattr(testset, "_gather_candidates", lambda: [])
    with pytest.raises(ValueError):
        testset.build_manifest("需求")


# ---- evolve 纯函数 ----


def test_composite():
    assert composite({"mean": 80.0, "sdv": 4.0}) == 74.0
    assert composite({"mean": None, "sdv": None}) is None
    assert composite({"mean": 70.0, "sdv": 0.0}) == 70.0


def _bank():
    alleles = {
        s: [{"id": f"{s.lower()}.{x}", "label": x, "text": f"{s} {x}"} for x in ("a", "b")]
        for s in ("G1", "G2", "G3", "G4", "G5")
    }
    return {"alleles": alleles, "variants": []}


def test_crossover_g1_fixed_and_slots_legal():
    bank = _bank()
    pa = {
        "id": "var.pa",
        "slots": {s: f"{s.lower()}.a" for s in ("G1", "G2", "G3", "G4", "G5")},
    }
    pb = {
        "id": "var.pb",
        "slots": {s: f"{s.lower()}.b" for s in ("G1", "G2", "G3", "G4", "G5")},
    }
    for seed in range(20):
        child = crossover(bank, pa, pb, new_id=f"var.x{seed}", rng=random.Random(seed))
        assert child["id"] == f"var.x{seed}"
        assert child["slots"]["G1"] == "g1.a"  # G1 固定取 parent_a
        for s in ("G2", "G3", "G4", "G5"):
            assert child["slots"][s] in {pa["slots"][s], pb["slots"][s]}
        for s, aid in child["slots"].items():
            assert aid in {a["id"] for a in bank["alleles"][s]}


def test_select_elites():
    cards = [
        {"variant_id": "a", "composite": 70.0, "mean": 75.0},
        {"variant_id": "b", "composite": 80.0, "mean": 82.0},
        {"variant_id": "c", "composite": None, "mean": None},
        {"variant_id": "d", "composite": 75.0, "mean": 76.0},
    ]
    elites = select_elites(cards, 2)
    assert [c["variant_id"] for c in elites] == ["b", "d"]
    assert select_elites(cards, 0) == []


def test_gate_verdict_flow():
    # 首代 promote
    assert gate_verdict([70.0], 1.0, 2)["verdict"] == "promote"
    # 提升不足 → stagnant
    v = gate_verdict([70.0, 70.5], 1.0, 2)
    assert v["verdict"] == "stagnant" and v["stagnant_count"] == 1
    # 连续停滞超限 → stop
    v = gate_verdict([70.0, 70.5, 70.9], 1.0, 2)
    assert v["verdict"] == "stop" and v["stagnant_count"] == 2
    # 达标提升 → promote 并重置停滞计数
    v = gate_verdict([70.0, 70.5, 73.0], 1.0, 2)
    assert v["verdict"] == "promote" and v["stagnant_count"] == 0
    assert v["improvement"] == 2.5


def test_attribute_failure():
    cards = [
        {
            "variant_id": "var.x",
            "cases": [
                {
                    "dimension_scores": {
                        "知识准确性": 60.0,
                        "指令遵循": 70.0,
                        "表达清晰": 90.0,
                    }
                },
                {
                    "dimension_scores": {
                        "知识准确性": 64.0,
                        "指令遵循": 72.0,
                        "表达清晰": 92.0,
                    }
                },
            ],
        }
    ]
    out = attribute_failure(cards)
    dims = [d["dimension"] for d in out["low_dims"]]
    assert dims[0] == "知识准确性"  # 均分最低排最前
    assert out["low_dims"][0]["mean"] == 62.0
    assert out["slot_hints"]["知识准确性"] == ["G3"]  # 知识类→G3
    assert out["slot_hints"]["指令遵循"] == ["G4", "G5"]  # 指令遵循类→G4/G5
    assert "知识准确性" in out["failure_notes"]
    assert attribute_failure([]) == {"low_dims": [], "slot_hints": {}, "failure_notes": ""}


# ---- paired_gate 按题配对显著性门禁 ----


def _by_case(base: dict[str, float], deltas: dict[str, float] | None = None) -> dict[str, list[float]]:
    """构造 case_key → 各 rep 分数；deltas 逐题叠加在均分上（rep 间带小噪声）。"""
    out = {}
    for key, m in base.items():
        mean = m + (deltas or {}).get(key, 0.0)
        out[key] = [mean - 0.4, mean, mean + 0.4]
    return out


_BASE = {"s/c0": 60.0, "s/c1": 65.0, "s/c2": 70.0, "s/c3": 55.0}


def test_paired_gate_promote():
    prev = _by_case(_BASE)
    champ = _by_case(_BASE, {"s/c0": 6.0, "s/c1": 8.0, "s/c2": 10.0, "s/c3": 7.0})
    r = paired_gate(champ, prev)
    assert r["verdict"] == "promote"
    assert r["method"] == "paired_t+bootstrap"
    assert r["n_cases"] == 4
    assert r["diff_mean"] == 7.75
    assert r["ci_low"] > 0
    assert r["p_value"] < 0.05
    json.dumps(r)  # 全部可 JSON 序列化


def test_paired_gate_regress():
    prev = _by_case(_BASE)
    champ = _by_case(_BASE, {"s/c0": -6.0, "s/c1": -8.0, "s/c2": -10.0, "s/c3": -7.0})
    r = paired_gate(champ, prev)
    assert r["verdict"] == "regress"
    assert r["ci_high"] < 0
    assert r["diff_mean"] == -7.75
    assert r["p_value"] < 0.05


def test_paired_gate_stagnant_noise():
    keys = [f"s/c{i}" for i in range(8)]
    base = {k: 60.0 + i for i, k in enumerate(keys)}
    deltas = {k: d for k, d in zip(keys, [5.0, -4.0, 3.0, -2.0, 1.0, -6.0, 2.0, -3.0])}
    r = paired_gate(_by_case(base, deltas), _by_case(base))
    assert r["verdict"] == "stagnant"
    assert r["ci_low"] < 0 < r["ci_high"]


def test_paired_gate_zero_diffs():
    prev = _by_case(_BASE)
    r = paired_gate(_by_case(_BASE), prev)
    assert r["verdict"] == "stagnant"
    assert r["diff_mean"] == 0.0
    assert r["p_value"] == 1.0  # 全零差值退化
    assert r["ci_low"] == 0.0 and r["ci_high"] == 0.0


def test_paired_gate_insufficient_data():
    prev = _by_case(_BASE)
    one = paired_gate({"s/c0": [80.0, 82.0]}, {"s/c0": [60.0, 61.0]})
    assert one["n_cases"] == 1
    assert one["method"] == "insufficient_data"
    assert one["verdict"] == "stagnant"  # 保守判停滞，调用方退回固定阈值
    assert one["p_value"] is None and one["ci_low"] is None
    empty = paired_gate({}, prev)
    assert empty["n_cases"] == 0 and empty["diff_mean"] is None
    # 共有题但一侧分数为空也视为数据不足
    partial = paired_gate({"s/c0": [], "s/c1": [80.0]}, {"s/c0": [60.0], "s/c1": [70.0]})
    assert partial["n_cases"] == 1


def test_paired_gate_reproducible_same_seed():
    keys = [f"s/c{i}" for i in range(8)]
    base = {k: 60.0 + i for i, k in enumerate(keys)}
    deltas = {k: d for k, d in zip(keys, [5.0, -4.0, 3.0, -2.0, 1.0, -6.0, 2.0, -3.0])}
    champ, prev = _by_case(base, deltas), _by_case(base)
    r1 = paired_gate(champ, prev, seed=42)
    r2 = paired_gate(champ, prev, seed=42)
    assert r1 == r2  # 同 seed 完全可复现
    r3 = paired_gate(champ, prev, seed=7)
    assert r3["verdict"] == r1["verdict"]  # 换 seed 结论仍一致（噪声情形）


# ---- 评分失败率与 unreliable ----


def test_select_elites_skips_unreliable():
    cards = [
        {"variant_id": "a", "composite": 90.0, "mean": 92.0, "unreliable": True},
        {"variant_id": "b", "composite": 70.0, "mean": 72.0},
        {"variant_id": "c", "composite": 80.0, "mean": 82.0, "unreliable": False},
    ]
    assert [c["variant_id"] for c in select_elites(cards, 3)] == ["c", "b"]


def test_summarize_failures():
    stats = {
        "var.a": {"failed_runs": 1, "total_runs": 6},
        "var.b": {"failed_runs": 4, "total_runs": 6},
    }
    out = summarize_failures(stats)
    assert out["global"] == {"failed_runs": 5, "total_runs": 12, "rate": round(5 / 12, 4)}
    assert out["by_variant"]["var.a"]["unreliable"] is False
    assert out["by_variant"]["var.a"]["rate"] == round(1 / 6, 4)
    assert out["by_variant"]["var.b"]["unreliable"] is True  # 失败率 > 50%
    assert summarize_failures({})["global"] == {
        "failed_runs": 0,
        "total_runs": 0,
        "rate": None,
    }


# ---- 进化主循环接线（全 mock，不调 LLM）----


def _mock_bank() -> dict:
    alleles = {
        s: [{"id": f"{s.lower()}.{x}", "label": x, "text": f"{s} {x}"} for x in ("a", "b")]
        for s in ("G1", "G2", "G3", "G4", "G5")
    }
    variants = [
        {
            "id": vid,
            "hash": f"h-{vid}",
            "title": vid,
            "slots": {s: f"{s.lower()}.a" for s in ("G1", "G2", "G3", "G4", "G5")},
        }
        for vid in ("var.a", "var.b")
    ]
    return {"meta": {}, "alleles": alleles, "variants": variants}


class _StubLog:
    token_usage: dict = {}

    def record_phase(self, *a, **k):
        pass

    def record_genomes(self, *a, **k):
        pass

    def write_local(self, *a, **k):
        pass


def test_evolve_run_paired_gate_and_failures(tmp_path, monkeypatch):
    bank = _mock_bank()
    manifest = {
        "id": "m_test",
        "demand": "d",
        "cases": [{"suite": "s", "id": f"c{i}", "level": "basic"} for i in range(3)],
    }
    monkeypatch.setattr(evolve, "EVOLVE_DIR", tmp_path)
    monkeypatch.setattr(evolve, "ROOT", tmp_path)  # report 落盘路径按 ROOT 求相对
    monkeypatch.setattr(
        evolve, "resolve_cases", lambda m, part="cases": [dict(c) for c in m.get(part) or []]
    )
    monkeypatch.setattr(evolve, "generate_case", lambda *a, **k: {"id": "anchor"})
    monkeypatch.setattr(evolve, "generate_genomes", lambda *a, **k: bank)
    monkeypatch.setattr(evolve, "refine_genomes", lambda *a, **k: {"alleles": {}, "variants": []})
    monkeypatch.setattr(evolve, "cache_get", lambda *a, **k: None)
    monkeypatch.setattr(evolve, "cache_put", lambda *a, **k: None)
    monkeypatch.setattr(evolve, "get_or_create_log", lambda *a, **k: _StubLog())

    calls: dict[tuple, int] = {}

    def fake_eval(*, api_key, model, case, bank, variant, rep, abort, meter=None):
        vid = str(variant["id"])
        key = (vid, case["id"], rep)
        gen = calls.get(key, 0)  # 同一 (vid, case, rep) 第 g 次被评 = 第 g 代
        calls[key] = gen + 1
        if vid == "var.a" and case["id"] == "c2" and rep == 2 and gen == 0:
            return {"variant_id": vid, "rep": rep, "score": None, "ok": False}  # 评分失败
        base = {"var.a": 60.0, "var.b": 70.0}.get(vid, 62.0)
        return {
            "variant_id": vid,
            "rep": rep,
            "score": base + 8.0 * gen,  # 每代 +8：gen1 冠军显著优于 gen0
            "ok": True,
            "dimension_scores": {},
        }

    monkeypatch.setattr(evolve, "_eval_one_variant", fake_eval)

    mgr = evolve.EvolveManager()
    run = mgr.start(
        "k",
        "m",
        manifest=manifest,
        max_generations=2,
        variants_per_gen=2,
        eval_reps=2,
        elite_k=1,
        workers=2,
        with_baseline=False,
    )
    deadline = time.time() + 30
    while run.status in ("pending", "running") and time.time() < deadline:
        time.sleep(0.05)
    assert run.status == "done", run.error

    # gen0：首代走固定阈值兜底（无配对数据）
    g0, g1 = run.gates
    assert g0["verdict"] == "promote" and g0["reason"] == "first_generation"
    assert g0["method"] == "fixed_threshold" and g0["paired"] is None
    # gen1：var.b 连任，两代独立采样按题配对 → 显著提升 promote
    assert g1["verdict"] == "promote"
    assert g1["method"] == "paired_t+bootstrap"
    assert g1["paired"]["n_cases"] == 3
    assert g1["paired"]["diff_mean"] == 8.0
    assert g1["paired"]["ci_low"] > 0
    assert g1["stagnant_count"] == 0
    assert run.champion["variant_id"] == "var.b"

    # 失败率：var.a gen0 c2 一次失败 → 全局 1/24
    snap = run.snapshot()
    assert snap["failure_stats"]["var.a"] == {"failed_runs": 1, "total_runs": 6}
    report = json.loads((tmp_path / run.id / "report.json").read_text(encoding="utf-8"))
    fr = report["failure_rates"]
    assert fr["global"] == {"failed_runs": 1, "total_runs": 24, "rate": round(1 / 24, 4)}
    assert fr["by_variant"]["var.a"]["failed_runs"] == 1
    assert fr["by_variant"]["var.a"]["unreliable"] is False
    md = (tmp_path / run.id / "report.md").read_text(encoding="utf-8")
    assert "## 评分失败率" in md and "1/24" in md

    # 墙钟：mark 带时间戳，report 含 wall_by_stage / wall_total_sec，md 含耗时分布表
    assert all(m.get("ts") for m in run.token_marks)
    assert report["wall_total_sec"] >= 0
    wall = report["wall_by_stage"]
    assert [s["stage"] for s in wall] == ["init", "gen0_eval", "gen0_refine", "gen1_eval"]
    assert all("seconds" in s and "pct" in s for s in wall)
    assert "## 耗时分布" in md and "总墙钟" in md

    # scorecard 落盘含 failures/total_runs 明细
    card = json.loads(
        (tmp_path / run.id / "gen0" / "scorecard_var.a.json").read_text(encoding="utf-8")
    )
    assert card["failures"] == 1 and card["total_runs"] == 6
    c2 = next(c for c in card["cases"] if c["id"] == "c2")
    assert c2["failures"] == 1 and c2["total_runs"] == 2
    assert c2["scores"] == [60.0]  # 成功 rep 的分数仍计入


# ---- 随机移民 ----


def test_random_immigrant():
    bank = _bank()
    imm = random_immigrant(bank, new_id="var.imm1_0", rng=random.Random(7))
    assert imm["id"] == "var.imm1_0"
    assert imm["role_in_demo"] == "immigrant"  # 来源可标识
    for s, aid in imm["slots"].items():
        assert aid in {a["id"] for a in bank["alleles"][s]}  # 每槽均为合法等位
    again = random_immigrant(bank, new_id="var.imm1_0", rng=random.Random(7))
    assert again["slots"] == imm["slots"]  # 同 rng seed 可复现
    empty = random_immigrant({"alleles": {}}, new_id="x", rng=random.Random(1))
    assert all(v == "" for v in empty["slots"].values())  # 无等位的槽给空串


# ---- 分层均分 ----


def test_stratify_scores():
    per_case = [
        {"suite": "s1", "id": "c0", "test_type": "text", "scores": [80.0, 82.0]},
        {"suite": "s1", "id": "c1", "test_type": "text", "scores": [84.0]},
        {"suite": "s2", "id": "c2", "test_type": "image", "scores": [40.0, 44.0]},
    ]
    out = stratify_scores(per_case)
    assert out["method"] == "test_type"  # 题型字段优先
    assert out["layers"]["text"]["n"] == 3
    assert out["layers"]["text"]["mean"] == 82.0
    assert out["layers"]["image"]["mean"] == 42.0
    # 无题型字段退回 suite 套件分层
    out2 = stratify_scores([{"suite": "s1", "id": "c0", "scores": [70.0]}])
    assert out2["method"] == "suite" and out2["layers"]["s1"]["mean"] == 70.0
    # 题型/套件都没有 → method=none 并注明无法分层的原因
    out3 = stratify_scores([{"id": "c0", "scores": [1.0]}])
    assert out3["method"] == "none" and out3["layers"] == {}
    assert "无法" in out3["note"]


# ---- refine_genomes 两档变异（mock LLM）----


def _refine_seed() -> dict:
    return {
        "variant_id": "var.seed",
        "slots": {s: f"{s.lower()}.seed" for s in ("G1", "G2", "G3", "G4", "G5")},
        "slot_texts": {
            s: {
                "allele_id": f"{s.lower()}.seed",
                "allele": {"id": f"{s.lower()}.seed", "label": s, "text": f"{s} seed"},
            }
            for s in ("G1", "G2", "G3", "G4", "G5")
        },
    }


def test_refine_genomes_wide_mode(monkeypatch):
    import generate

    captured: dict = {}
    data = {
        "alleles": {"G1": [{"id": "g1.new", "label": "new", "text": "new identity"}]},
        "variants": [
            {
                "id": "var.w",
                "title": "重写",
                "slots": {
                    "G1": "g1.new",
                    "G2": "g2.seed",
                    "G3": "g3.seed",
                    "G4": "g4.seed",
                    "G5": "g5.seed",
                },
            }
        ],
    }

    def fake_chat(api_key, model, system, user, **kw):
        captured["system"] = system
        return data

    monkeypatch.setattr(generate, "_chat_json", fake_chat)
    case = {"id": "anchor", "title": "t"}
    wide_bank = generate.refine_genomes("k", "m", case, _refine_seed(), mode="wide")
    assert "大开角重写" in captured["system"]
    vw = next(v for v in wide_bank["variants"] if v["id"] == "var.w")
    assert vw["slots"]["G1"] == "g1.new"  # wide：不固定 G1
    local_bank = generate.refine_genomes("k", "m", case, _refine_seed())
    assert "邻域" in captured["system"]
    vl = next(v for v in local_bank["variants"] if v["id"] == "var.w")
    assert vl["slots"]["G1"] == "g1.seed"  # local（默认）：G1 固定为种子


# ---- 自适应变异 + 随机移民 + 分层报告接线（全 mock，不调 LLM）----


def test_evolve_run_adaptive_mutation_and_immigrants(tmp_path, monkeypatch):
    bank = _mock_bank()
    manifest = {
        "id": "m_test2",
        "demand": "d",
        "cases": [
            {
                "suite": "s",
                "id": f"c{i}",
                "level": "basic",
                "test_type": "text" if i < 2 else "image",
            }
            for i in range(3)
        ],
    }
    monkeypatch.setattr(evolve, "EVOLVE_DIR", tmp_path)
    monkeypatch.setattr(evolve, "ROOT", tmp_path)
    monkeypatch.setattr(
        evolve, "resolve_cases", lambda m, part="cases": [dict(c) for c in m.get(part) or []]
    )
    monkeypatch.setattr(evolve, "generate_case", lambda *a, **k: {"id": "anchor"})
    monkeypatch.setattr(evolve, "generate_genomes", lambda *a, **k: bank)
    monkeypatch.setattr(evolve, "cache_get", lambda *a, **k: None)
    monkeypatch.setattr(evolve, "cache_put", lambda *a, **k: None)

    modes: list[str] = []

    def fake_refine(*a, **k):
        modes.append(k.get("mode", "local"))
        return {"alleles": {}, "variants": []}

    monkeypatch.setattr(evolve, "refine_genomes", fake_refine)

    genome_banks: list[dict] = []

    class _RecLog(_StubLog):
        def record_genomes(self, *a, **k):
            if k.get("bank"):
                genome_banks.append(k["bank"])

    monkeypatch.setattr(evolve, "get_or_create_log", lambda *a, **k: _RecLog())

    def fake_eval(*, api_key, model, case, bank, variant, rep, abort, meter=None):
        vid = str(variant["id"])
        # 各代分数全平 → 配对门禁判停滞（零提升、冠军连任的冒烟情形）
        base = 70.0 if vid == "var.b" else 60.0
        return {
            "variant_id": vid,
            "rep": rep,
            "score": base,
            "ok": True,
            "dimension_scores": {},
        }

    monkeypatch.setattr(evolve, "_eval_one_variant", fake_eval)

    mgr = evolve.EvolveManager()
    run = mgr.start(
        "k",
        "m",
        manifest=manifest,
        max_generations=3,
        variants_per_gen=4,
        eval_reps=2,
        elite_k=1,
        workers=2,
        stagnation_limit=2,
        with_baseline=False,
    )
    deadline = time.time() + 30
    while run.status in ("pending", "running") and time.time() < deadline:
        time.sleep(0.05)
    assert run.status == "done", run.error

    # 自适应变异：gen0 后 local（邻域精炼），gen1 停滞后 wide（大开角重写）
    assert modes == ["local", "wide"]
    # gen1/gen2 连续停滞达 limit → stop（门禁记录带配对显著性）
    assert run.gates[1]["verdict"] == "stagnant"
    assert run.gates[1]["method"] == "paired_t+bootstrap"
    assert run.gates[2]["verdict"] == "stop"

    # 随机移民：每代 1–2 个，种群中可标识来源
    last_bank = genome_banks[-1]
    imm = [v for v in last_bank["variants"] if v.get("role_in_demo") == "immigrant"]
    assert 1 <= len(imm) <= 2

    # report：进化算子记录 + 冠军分层均分
    report = json.loads((tmp_path / run.id / "report.json").read_text(encoding="utf-8"))
    ops = report["evolution_ops"]
    assert [o["mutation_level"] for o in ops] == ["local", "wide"]
    assert all(1 <= len(o["immigrants"]) <= 2 for o in ops)
    strat = report["champion_stratified"]
    assert strat["method"] == "test_type"
    assert set(strat["layers"]) == {"text", "image"}
    assert strat["layers"]["text"]["mean"] == 70.0  # 冠军 var.b 全 70 分
    md = (tmp_path / run.id / "report.md").read_text(encoding="utf-8")
    assert "## 进化算子" in md and "大开角重写" in md
    assert "冠军分层均分" in md


# ---- 墙钟分阶段汇总（注入假时间）----


def test_wall_by_stage_fake_clock():
    marks = [
        {"stage": "init", "ts": 105.0},
        {"stage": "gen0_eval", "ts": 165.0},
        {"stage": "gen0_refine", "ts": 175.0},
    ]
    rows = wall_by_stage(marks, t0=100.0)
    assert [r["stage"] for r in rows] == ["init", "gen0_eval", "gen0_refine"]
    assert [r["seconds"] for r in rows] == [5.0, 60.0, 10.0]  # 首段从 t0 起算
    assert [r["pct"] for r in rows] == [6.7, 80.0, 13.3]  # 占总墙钟百分比
    json.dumps(rows)  # 可 JSON 序列化


def test_wall_by_stage_degenerate():
    # 零墙钟：pct 记 None，不除零
    zero = wall_by_stage([{"stage": "init", "ts": 100.0}], t0=100.0)
    assert zero[0]["seconds"] == 0.0 and zero[0]["pct"] is None
    # 无 mark / mark 缺 ts：安全退化
    assert wall_by_stage([], t0=1.0) == []
    rows = wall_by_stage([{"stage": "init"}, {"stage": "gen0_eval", "ts": 9.0}], t0=3.0)
    assert [r["seconds"] for r in rows] == [0.0, 6.0]
