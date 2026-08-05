"""Tests for `yiagent hof pull`: mocked HTTP, no live server / network."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from yiagent import hof_pull
from yiagent.cli.main import main

GENE_HASH = "yg-test-abc123"


def _genome_payload(gene_hash: str = GENE_HASH) -> dict:
    """与服务端 GET /api/hof/genome/{gene_hash} 返回同构的最小 payload。"""
    slots = {s: f"{s.lower()}.x" for s in ("G1", "G2", "G3", "G4", "G5")}
    return {
        "gene_hash": gene_hash,
        "variant_id": "var.hof_champ",
        "title": "hof champion",
        "bank": {
            "alleles": {
                s: [{"id": aid, "label": aid, "text": f"{aid} text"}]
                for s, aid in slots.items()
            },
            "variants": [
                {"id": "var.hof_champ", "title": "hof champion", "hash": gene_hash, "slots": slots}
            ],
        },
        "slots": slots,
        "slot_texts": {},
    }


class _FakeResp:
    """模拟 urllib.request.urlopen 的上下文管理器响应。"""

    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _mock_urlopen_ok(monkeypatch, payload: dict) -> list[str]:
    urls: list[str] = []

    def fake(url, timeout=None, **kw):
        req = url
        urls.append(getattr(req, "full_url", str(req)))
        return _FakeResp(payload)

    monkeypatch.setattr(hof_pull.urllib.request, "urlopen", fake)
    return urls


def _mock_urlopen_http_error(monkeypatch, code: int):
    def fake(url, timeout=None, **kw):
        req = url
        full = getattr(req, "full_url", str(req))
        raise urllib.error.HTTPError(full, code, "err", hdrs=None, fp=io.BytesIO(b""))

    monkeypatch.setattr(hof_pull.urllib.request, "urlopen", fake)


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("YIAGENT_HOME", str(tmp_path))
    return tmp_path


def test_pull_success_saves_genome(home, monkeypatch):
    urls = _mock_urlopen_ok(monkeypatch, _genome_payload())
    path = hof_pull.pull_genome(GENE_HASH, base_url="http://hof.test:8788", home=home)
    assert urls == [f"http://hof.test:8788/api/hof/genome/{GENE_HASH}"]
    assert path == home / "hof" / f"genome_{GENE_HASH}.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["gene_hash"] == GENE_HASH
    assert saved["bank"]["variants"][0]["id"] == "var.hof_champ"
    # 落盘包可直接被 improve --apply 消费（bank 分支）
    from yiagent.improve_pack import apply_best_genome

    info = apply_best_genome(path, home)
    assert info["variant_id"] == "var.hof_champ"


def test_pull_hash_mismatch_rejected(home, monkeypatch):
    _mock_urlopen_ok(monkeypatch, _genome_payload(gene_hash="yg-other-999"))
    with pytest.raises(hof_pull.HofPullError, match="不匹配"):
        hof_pull.pull_genome(GENE_HASH, base_url="http://hof.test:8788", home=home)
    # 校验失败不落盘
    assert not (home / "hof").exists()


def test_pull_incomplete_bank_rejected(home, monkeypatch):
    bad = _genome_payload()
    bad["bank"] = {"alleles": {}}
    _mock_urlopen_ok(monkeypatch, bad)
    with pytest.raises(hof_pull.HofPullError, match="bank"):
        hof_pull.pull_genome(GENE_HASH, base_url="http://hof.test:8788", home=home)


def test_pull_404(home, monkeypatch):
    _mock_urlopen_http_error(monkeypatch, 404)
    with pytest.raises(hof_pull.HofPullError, match="404"):
        hof_pull.pull_genome(GENE_HASH, base_url="http://hof.test:8788", home=home)


def test_pull_url_not_configured(home, monkeypatch):
    monkeypatch.delenv("YIAGENT_HOF_URL", raising=False)
    with pytest.raises(hof_pull.HofPullError, match="YIAGENT_HOF_URL"):
        hof_pull.pull_genome(GENE_HASH, home=home)


def test_pull_url_from_env(home, monkeypatch):
    monkeypatch.setenv("YIAGENT_HOF_URL", "http://env-hof:9000/")
    urls = _mock_urlopen_ok(monkeypatch, _genome_payload())
    hof_pull.pull_genome(GENE_HASH, home=home)
    assert urls == [f"http://env-hof:9000/api/hof/genome/{GENE_HASH}"]


def test_cli_hof_pull(home, monkeypatch, capsys):
    monkeypatch.setenv("YIAGENT_HOF_URL", "http://env-hof:9000")
    _mock_urlopen_ok(monkeypatch, _genome_payload())
    code = main(["hof", "pull", GENE_HASH])
    assert code == 0
    out = capsys.readouterr().out
    assert "improve --apply" in out
    assert (home / "hof" / f"genome_{GENE_HASH}.json").is_file()


def test_cli_hof_pull_no_url(home, monkeypatch, capsys):
    monkeypatch.delenv("YIAGENT_HOF_URL", raising=False)
    code = main(["hof", "pull", GENE_HASH])
    assert code == 1
    assert "YIAGENT_HOF_URL" in capsys.readouterr().err
