"""名人堂服务端测试：提交 → 聚合 → 排行榜 / genome / alleles / 校验 / 限流。

全离线：fastapi TestClient + tmp_path SQLite，不起真实服务。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "hof" / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from fastapi.testclient import TestClient  # noqa: E402

from aggregate import beta_shrink, merge_weighted_mean_sdv  # noqa: E402
from app import create_app  # noqa: E402


def _genome(gene_hash: str, variant_id: str = "var.1", allele_text: str = "保持批判性追问。"):
    return {
        "gene_hash": gene_hash,
        "bank": {
            "alleles": {
                slot: [{"id": f"{slot.lower()}.a1", "label": f"{slot} 等位甲", "text": allele_text}]
                for slot in ("G1", "G2", "G3", "G4", "G5")
            },
            "variants": [
                {
                    "id": variant_id,
                    "title": "批判型写手",
                    "hash": gene_hash,
                    "slots": {slot: f"{slot.lower()}.a1" for slot in ("G1", "G2", "G3", "G4", "G5")},
                }
            ],
        },
        "variant_id": variant_id,
    }


def _submission(gene_hash: str = "h" * 64, *, contributor: str = "anon_a",
                model: str = "k3", mean: float = 90.0, sdv: float = 1.0,
                composite: float = 88.0, n: int = 10,
                dim_means: dict | None = None, suite: str = "xsct-l",
                allele_text: str = "保持批判性追问。"):
    return {
        "schema": "yiagent.hof.submission",
        "version": "0.1",
        "contributor_id": contributor,
        "submitted_at": "2026-07-31T00:00:00+00:00",
        "genome": _genome(gene_hash, allele_text=allele_text),
        "evaluation": {
            "model": model,
            "testset": {"kind": "xsct", "cases": [{"suite": suite, "id": "l_1", "level": "basic"}]},
            "reps": 2,
            "stats": {"mean": mean, "sdv": sdv, "composite": composite, "n": n},
            "per_case": [{"suite": suite, "id": "l_1", "mean": mean, "sdv": sdv}],
            "dim_means": dim_means if dim_means is not None else {"instruction_following": 92.0},
        },
        "context": {
            "yiagent_version": "0.2.0",
            "evolve": {"generation": 3, "run_id_hash": "abc"},
            "demand_tags": ["批判思维", "写作"],
        },
    }


@pytest.fixture()
def client(tmp_path):
    app = create_app(tmp_path / "hof.db")
    with TestClient(app) as c:
        yield c


# ---------------- 提交 → 聚合 → 排行榜 ----------------

def test_submit_and_leaderboard_shrink_direction(client):
    # 基因组 A：高分但 n 小 → 应向 prior=75 收缩
    sub_a = _submission("a" * 64, mean=99.0, sdv=0.5, composite=99.0, n=1)
    # 基因组 B：分数略低但 n 大 → 收缩少，应排在 A 前
    sub_b = _submission("b" * 64, mean=92.0, sdv=1.0, composite=92.0, n=50)
    r = client.post("/api/hof/submit", json={"submissions": [sub_a, sub_b]})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 2 and body["rejected"] == 0

    lb = client.get("/api/hof/leaderboard", params={"min_n": 1}).json()["items"]
    assert [x["gene_hash"] for x in lb] == ["b" * 64, "a" * 64]
    shrunk_a = next(x["shrunk"] for x in lb if x["gene_hash"] == "a" * 64)
    shrunk_b = next(x["shrunk"] for x in lb if x["gene_hash"] == "b" * 64)
    # n=1 的显著向 75 收缩；n=50 的几乎不动
    assert shrunk_a == pytest.approx((1 * 99.0 + 5 * 75.0) / 6, abs=1e-3)
    assert shrunk_a < 80.0
    assert shrunk_b == pytest.approx((50 * 92.0 + 5 * 75.0) / 55, abs=1e-3)
    assert shrunk_b > 90.0


def test_weighted_merge_same_gene(client):
    # 同 gene_hash 两次上报：n 加权合并 mean
    s1 = _submission("c" * 64, mean=80.0, composite=80.0, n=10)
    s2 = _submission("c" * 64, contributor="anon_b", mean=90.0, composite=90.0, n=30)
    client.post("/api/hof/submit", json={"submissions": [s1, s2]})
    lb = client.get("/api/hof/leaderboard", params={"min_n": 1}).json()["items"]
    assert len(lb) == 1
    item = lb[0]
    assert item["n"] == 40
    assert item["mean"] == pytest.approx((10 * 80.0 + 30 * 90.0) / 40, abs=1e-3)


def test_gene_hash_dedup(client):
    subs = [_submission("d" * 64, contributor=f"anon_{i}") for i in range(3)]
    client.post("/api/hof/submit", json={"submissions": subs})
    stats = client.get("/api/hof/stats").json()
    assert stats["submissions_accepted"] == 3
    assert stats["genomes"] == 1
    assert stats["contributors"] == 3
    genome = client.get(f"/api/hof/genome/{'d' * 64}").json()
    assert genome["n_submissions"] == 3


def test_min_n_threshold(client):
    client.post("/api/hof/submit", json=_submission("e" * 64, n=2))
    assert client.get("/api/hof/leaderboard", params={"min_n": 3}).json()["items"] == []
    assert len(client.get("/api/hof/leaderboard", params={"min_n": 2}).json()["items"]) == 1


def test_leaderboard_filters(client):
    client.post("/api/hof/submit", json={"submissions": [
        _submission("f" * 64, model="k3", suite="xsct-l", dim_means={"crit": 90.0}),
        _submission("0" * 64, model="deepseek", suite="xsct-m", dim_means={"math": 80.0}),
    ]})
    lb = client.get("/api/hof/leaderboard", params={"min_n": 0, "model": "k3"}).json()["items"]
    assert [x["gene_hash"] for x in lb] == ["f" * 64]
    lb = client.get("/api/hof/leaderboard", params={"min_n": 0, "suite": "xsct-m"}).json()["items"]
    assert [x["gene_hash"] for x in lb] == ["0" * 64]
    lb = client.get("/api/hof/leaderboard", params={"min_n": 0, "dimension": "crit"}).json()["items"]
    assert [x["gene_hash"] for x in lb] == ["f" * 64]


# ---------------- schema 校验拒收 ----------------

@pytest.mark.parametrize("mutate,reason_part", [
    (lambda s: s.update(version="9.9"), "version"),
    (lambda s: s.pop("contributor_id"), "contributor_id"),
    (lambda s: s["genome"].pop("gene_hash"), "gene_hash"),
    (lambda s: s["evaluation"].pop("model"), "model"),
    (lambda s: s["evaluation"].update(model="x" * 200), "上限"),
    (lambda s: s.update(contributor_id="y" * 200), "上限"),
    (lambda s: s["evaluation"]["stats"].update(composite=140.0), "[0, 100]"),
    (lambda s: s["evaluation"]["stats"].pop("n"), "mean/sdv/composite/n"),
])
def test_schema_rejections(client, mutate, reason_part):
    sub = _submission("1" * 64)
    mutate(sub)
    r = client.post("/api/hof/submit", json=sub)
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 0 and body["rejected"] == 1
    assert reason_part in body["results"][0]["reason"]


def test_rubric_keyword_rejected(client):
    sub = _submission("2" * 64, allele_text="严格对照评分标准 rubric 逐条给分。")
    r = client.post("/api/hof/submit", json=sub)
    body = r.json()
    assert body["accepted"] == 0
    assert "评分标准" in body["results"][0]["reason"] or "rubric" in body["results"][0]["reason"]
    # 拒收不进 genome 库
    assert client.get(f"/api/hof/genome/{'2' * 64}").status_code == 404


def test_extra_fields_dropped(client):
    sub = _submission("3" * 64)
    sub["api_key"] = "sk-should-never-ship"
    sub["genome"]["local_path"] = "/Users/x/private"
    r = client.post("/api/hof/submit", json=sub).json()
    assert r["accepted"] == 1
    dropped = r["results"][0]["dropped_fields"]
    assert "api_key" in dropped and "genome.local_path" in dropped
    # 落库的 genome 也不含多余字段
    genome = client.get(f"/api/hof/genome/{'3' * 64}").json()
    assert "local_path" not in genome["bank"] and "local_path" not in str(genome)


# ---------------- 限流 ----------------

def test_rate_limit_429(client):
    # 同一 contributor 每分钟 30 份：前 30 份接收，第 31 份整批被限流 → 429
    for i in range(30):
        r = client.post("/api/hof/submit", json=_submission(f"{i:064x}"))
        assert r.status_code == 200 and r.json()["accepted"] == 1
    r = client.post("/api/hof/submit", json=_submission("f" * 64))
    assert r.status_code == 429
    assert r.json()["results"][0]["status"] == "rejected"
    assert "rate_limited" in r.json()["results"][0]["reason"]
    # 换一个 contributor 不受影响
    r = client.post("/api/hof/submit", json=_submission("9" * 64, contributor="anon_other"))
    assert r.status_code == 200 and r.json()["accepted"] == 1


# ---------------- genome 下载可作 seed ----------------

def test_genome_download_seed_format(client):
    client.post("/api/hof/submit", json=_submission("4" * 64))
    r = client.get(f"/api/hof/genome/{'4' * 64}")
    assert r.status_code == 200
    g = r.json()
    # 完整 bank + variant，且 slots/slot_texts 与 factory bank_from_improve_seed 的入参同构
    assert set(g["bank"]["alleles"].keys()) == {"G1", "G2", "G3", "G4", "G5"}
    assert g["variant_id"] == "var.1"
    assert g["slots"]["G1"] == "g1.a1"
    st = g["slot_texts"]["G1"]
    assert st["allele_id"] == "g1.a1"
    assert st["allele"]["text"] == "保持批判性追问。"
    assert client.get("/api/hof/genome/nonexistent").status_code == 404


# ---------------- alleles 端点 ----------------

def test_allele_performance(client):
    # 两个基因组共享同一套等位 id，composite 不同 → 平均
    s1 = _submission("5" * 64, composite=80.0, dim_means={"crit": 80.0})
    s2 = _submission("6" * 64, composite=90.0, dim_means={"crit": 100.0})
    client.post("/api/hof/submit", json={"submissions": [s1, s2]})
    r = client.get("/api/hof/alleles", params={"slot": "G5"})
    items = r.json()["items"]
    assert len(items) == 1
    a = items[0]
    assert a["allele_id"] == "g5.a1"
    assert a["n_genomes"] == 2 and a["appearances"] == 2
    assert a["composite"] == pytest.approx(85.0)
    assert a["dim_means"]["crit"] == pytest.approx(90.0)


# ---------------- 聚合纯函数 ----------------

def test_aggregate_pure_functions():
    mean, sdv, n = merge_weighted_mean_sdv([(80.0, 0.0, 10), (90.0, 0.0, 30)])
    assert mean == pytest.approx(87.5)
    assert sdv == pytest.approx(( (10 * 80.0**2 + 30 * 90.0**2) / 40 - 87.5**2 ) ** 0.5)
    assert n == 40
    assert beta_shrink(100.0, 0) == 75.0          # 无样本 → 全收缩到 prior
    assert beta_shrink(100.0, 1_000_000) == pytest.approx(100.0, abs=0.01)  # 大样本 ≈ 原值


# ---------------- 提交流水与健康检查 ----------------

def test_submissions_feed_and_health(client):
    client.post("/api/hof/submit", json=_submission("7" * 64))
    bad = _submission("8" * 64)
    bad["version"] = "9.9"
    client.post("/api/hof/submit", json=bad)
    feed = client.get("/api/hof/submissions").json()["items"]
    assert len(feed) == 2
    by_hash = {x["gene_hash"]: x for x in feed}
    assert by_hash["7" * 64]["status"] == "accepted"
    assert by_hash["8" * 64]["status"] == "rejected"
    assert "version" in by_hash["8" * 64]["reason"]

    health = client.get("/api/health").json()
    assert health["ok"] and health["service"] == "yiagent-hof"
