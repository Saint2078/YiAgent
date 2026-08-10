"""目标 A（AI 科普串联助手）收尾核验：manifest / 种子基因组 / 裁判接线。

全程离线：不起服务、不调 LLM（judge 用 mock）、不读密钥。
容器镜像默认 YIAGENT_CASE_ROOT=/app/case/xsct，本文件用 fixture 指到仓库 case/ 总目录。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "factory" / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import assemble  # noqa: E402
import generate  # noqa: E402
import judge  # noqa: E402
import preflight  # noqa: E402
from case_library import LIBRARY  # noqa: E402
from testset import MANIFEST_DIR, load_manifest, resolve_cases  # noqa: E402

MANIFEST_ID = "0803c197a73c"
SEED_PATH = REPO / "factory" / "fixtures" / "seed" / "ai_kepu_seed.json"
SLOTS = ("G1", "G2", "G3", "G4", "G5")
# 五维裁判维度 id（见评测包 01-裁判与门禁）：禁止出现在等位文本里（告知≠提升）
DIM_IDS = (
    "accuracy_verified",
    "structure_chain",
    "readability_wechat",
    "boundary_honesty",
    "no_hype",
)
EXPECTED_WEIGHTS = {"accuracy_verified": 25, "structure_chain": 25,
                    "readability_wechat": 25, "boundary_honesty": 15, "no_hype": 10}


@pytest.fixture()
def kepu_cases(monkeypatch):
    """把题库来源指到仓库 case/ 总目录（含 ai_科普 + xsct），结束后还原。"""
    monkeypatch.setenv("YIAGENT_CASE_ROOT", str(REPO / "case"))
    LIBRARY.reload()
    yield
    LIBRARY.reload()


def _load_seed() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


# ---- A3A：manifest 可加载 + preflight 无 errors ----

# manifest 落在 factory/save/（被 .gitignore 排除的运行时产物），新克隆的仓里没有。
# 缺数据是「跑不了」不是「跑挂了」：给 skip 并说清怎么补，别让新克隆看到两条红。
_MANIFEST_PATH = MANIFEST_DIR / f"{MANIFEST_ID}.json"
needs_manifest = pytest.mark.skipif(
    not _MANIFEST_PATH.is_file(),
    reason=(
        f"缺本地 manifest {_MANIFEST_PATH}（factory/save/ 未入库）；"
        "在 factory 控制台生成同 id 的题集清单后本用例自动生效"
    ),
)


@needs_manifest
def test_manifest_loads_and_composition(kepu_cases):
    m = load_manifest(MANIFEST_ID)
    assert m["schema"] == "yiagent.factory.testset"
    cases, hold = m["cases"], m["holdout"]
    assert len(cases) == 8 and len(hold) == 4  # 8+4：holdout 落在 3–5 区间
    assert all(c["suite"] == "科普短文" for c in cases + hold)  # 单一套件
    assert all(c["level"] == "basic" for c in cases + hold)
    evo_ids = {c["id"] for c in cases}
    hold_ids = {c["id"] for c in hold}
    assert not (evo_ids & hold_ids)  # 进化集与 holdout 不相交
    assert len(evo_ids | hold_ids) == 12  # 12 题全覆盖
    # 进化集覆盖全部 5 个维度标签（串联/短文/查证/边界/产品）
    full = resolve_cases(m, "cases")
    dims = {LIBRARY.get_raw("科普短文", c["id"]).get("dimension") for c in cases}
    assert dims == {"串联", "短文", "查证", "边界", "产品"}
    # 每题 criteria 五维齐全、权重和 100、rubric 非空
    for case in full + resolve_cases(m, "holdout"):
        crit = case.get("criteria") or {}
        assert {k: v.get("weight") for k, v in crit.items()} == EXPECTED_WEIGHTS
        assert all(v.get("rubric") for v in crit.values())
        assert case.get("messages") and case["messages"][0]["role"] == "system"


@needs_manifest
def test_manifest_preflight_no_errors(kepu_cases, monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "CACHE_DIR", tmp_path / "eval_cache")
    rep = preflight.run_preflight(manifest_id=MANIFEST_ID, api_key="x" * 12)
    assert rep["errors"] == []  # holdout 题数与混题型检查均通过
    assert rep["checks"]["manifest"] == {"id": MANIFEST_ID, "cases": 8, "holdout": 4}
    dist = rep["checks"]["distribution"]
    assert dist["test_types"] == {"ai_科普": 12}  # 单题型
    assert dist["suites"] == {"科普短文": 12}  # 单套件
    assert not any("混题型" in w or "跨套件" in w for w in rep["warnings"])


# ---- A2：种子基因组 bank 结构合法 + 种子 variant 槽位齐 + 黑盒约束 ----


def test_seed_bank_schema(kepu_cases):
    seed = _load_seed()
    bank = seed["bank"]
    alleles = bank["alleles"]
    assert set(alleles) == set(SLOTS)
    for slot in SLOTS:
        rows = alleles[slot]
        assert 2 <= len(rows) <= 3  # 每槽 2–3 个等位
        ids = [a["id"] for a in rows]
        assert len(ids) == len(set(ids))  # 槽内 id 唯一
        for a in rows:
            assert a.get("id") and a.get("label") and str(a.get("text") or "").strip()
    # 种子 variant：槽位齐 G1–G5 且引用存在的等位 id
    variants = bank["variants"]
    assert 1 <= len(variants) <= 2
    legal = {s: {a["id"] for a in alleles[s]} for s in SLOTS}
    for v in variants:
        assert set(v["slots"]) == set(SLOTS)
        assert all(v["slots"][s] in legal[s] for s in SLOTS)
        assert v.get("id") and v.get("hash") and v.get("title")


def test_seed_dict_matches_evolve_start_contract(kepu_cases):
    """顶层 slots/slot_texts 与 bank_from_improve_seed 入参同构，可直接作 evolve/start 的 seed。"""
    seed = _load_seed()
    assert seed["variant_id"] == "var.kepu.seed_a"
    assert set(seed["slots"]) == set(SLOTS)
    for slot in SLOTS:
        st = seed["slot_texts"][slot]
        assert st["allele_id"] == seed["slots"][slot]
        assert st["allele"]["id"] == st["allele_id"]
        assert st["allele"]["text"].strip()
    # factory 侧既有消费逻辑能重建 bank（纯函数，不调 LLM）
    rebuilt = generate.bank_from_improve_seed(seed, {"id": "anchor", "title": "t"})
    assert all(rebuilt["alleles"][s] for s in SLOTS)
    v0 = rebuilt["variants"][0]
    assert v0["id"] == "var.kepu.seed_a"
    assert set(v0["slots"]) == set(SLOTS)
    assert v0["slots"]["G1"] == seed["slots"]["G1"]  # G1 固定为种子身份


def test_seed_alleles_no_rubric_leak(kepu_cases):
    """A2C 黑盒约束：等位文本不得灌装裁判维度 id / 权重 / rubric 分档原文。"""
    seed = _load_seed()
    for slot in SLOTS:
        for a in seed["bank"]["alleles"][slot]:
            text = a["text"]
            for dim in DIM_IDS:
                assert dim not in text, f"{a['id']} 泄漏维度 id {dim}"
            assert "weight" not in text and "权重" not in text
            assert "90-100" not in text and "90–100" not in text


# ---- A3B：裁判接线——真实题库第一题，mock LLM，验证加权分与 rubric 入 prompt ----


def test_judge_body_pulls_case_criteria(kepu_cases):
    case = LIBRARY.to_factory_case("科普短文", "pop_chain_001", "basic")
    body = assemble.judge_body(case)
    assert set(body["criteria"]) == set(EXPECTED_WEIGHTS)
    assert body["requirements"]  # 题面 requirements 进入 judge body
    # rubric 与 weight 进入 judge prompt（weight 标注为「仅用于加权」）
    msgs = judge.build_judge_messages(body, "样例回答正文")
    user = msgs[1]["content"]
    assert "weight=25" in user and "仅用于加权" in user
    assert "90-100" in user  # 四档标尺进入 prompt
    assert "关键事实正确" in user  # 本题 rubric 原文进入 prompt
    assert "样例回答正文" in user


def test_judge_weighted_score_with_real_case(kepu_cases, monkeypatch):
    case = LIBRARY.to_factory_case("科普短文", "pop_chain_001", "basic")
    body = assemble.judge_body(case)
    fake = json.dumps(
        {
            "dimension_scores": {
                "accuracy_verified": {"score": 88, "reason": "r"},
                "structure_chain": {"score": 92, "reason": "r"},
                "readability_wechat": {"score": 80, "reason": "r"},
                "boundary_honesty": {"score": 90, "reason": "r"},
                "no_hype": {"score": 70, "reason": "r"},
            },
            "overall_score": 99,  # 故意给错：工程侧应以加权重算为准
            "overall_comment": "c",
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(judge, "chat_completions", lambda *a, **k: {})
    monkeypatch.setattr(judge, "extract_content", lambda g: fake)
    out = judge.judge_once("k", "m", body, "候选回答")
    # (88*25 + 92*25 + 80*25 + 90*15 + 70*10) / 100 = 85.5
    assert out["score"] == 85.5
    assert out["ok"] is True
    assert out["scores_used"] == {
        "accuracy_verified": 88.0,
        "structure_chain": 92.0,
        "readability_wechat": 80.0,
        "boundary_honesty": 90.0,
        "no_hype": 70.0,
    }
