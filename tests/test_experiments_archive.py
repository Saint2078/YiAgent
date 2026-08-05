"""Tests for experiments/archive_evolve_run.py（tmp_path 往返，本机逻辑不入 Docker 依赖）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "experiments"))

import archive_evolve_run as arch  # noqa: E402

_NOW = 1_700_000_000.0  # 2023-11-14T22:13:20Z（固定时钟，目录名可断言）


def _fake_run_dir(tmp_path: Path, *, with_md: bool = True) -> Path:
    run_dir = tmp_path / "save" / "evolve" / "abc123"
    run_dir.mkdir(parents=True)
    report = {
        "run_id": "abc123",
        "model": "k3",
        "stop_reason": "max_generations",
        "wall_total_sec": 12.3,
        "wall_by_stage": [{"stage": "init", "seconds": 1.2, "pct": 9.8}],
        "manifest": {"id": "m_x", "cases": 6, "holdout": 3},
        "params": {"max_generations": 4, "eval_reps": 2, "manifest_cases": 6},
    }
    (run_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if with_md:
        (run_dir / "report.md").write_text("# 报告", encoding="utf-8")
    return run_dir


def test_archive_roundtrip(tmp_path):
    run_dir = _fake_run_dir(tmp_path)
    dest = arch.archive_run(run_dir, tmp_path / "experiments", now=_NOW)
    assert dest.name == "20231114_abc123"
    copied = json.loads((dest / "report.json").read_text(encoding="utf-8"))
    assert copied["run_id"] == "abc123"
    assert copied["wall_by_stage"][0]["stage"] == "init"
    assert (dest / "report.md").read_text(encoding="utf-8") == "# 报告"
    readme = (dest / "README.md").read_text(encoding="utf-8")
    # README 记录复跑口径：run id / manifest id / preflight / 启动命令 / env
    assert "abc123" in readme and "m_x" in readme
    assert "/api/evolve/preflight" in readme
    assert "/api/evolve/start" in readme
    assert "YIAGENT_HOF_ENABLED" in readme
    assert '"max_generations": 4' in readme


def test_archive_without_report_md(tmp_path):
    run_dir = _fake_run_dir(tmp_path, with_md=False)
    dest = arch.archive_run(run_dir, tmp_path / "out", now=_NOW)
    assert (dest / "report.json").is_file()
    assert not (dest / "report.md").exists()  # 缺 md 不报错，只缺该文件
    assert (dest / "README.md").is_file()


def test_archive_missing_report_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        arch.archive_run(tmp_path / "nope", tmp_path / "out")


def test_archive_main_by_run_id(tmp_path, capsys):
    _fake_run_dir(tmp_path)
    rc = arch.main(
        [
            "abc123",
            "--save-dir",
            str(tmp_path / "save" / "evolve"),
            "--out-dir",
            str(tmp_path / "exp"),
        ]
    )
    assert rc == 0
    assert "已归档" in capsys.readouterr().out
    assert (tmp_path / "exp" / f"{arch.time.strftime('%Y%m%d', arch.time.gmtime())}_abc123").is_dir()


def test_archive_main_missing_returns_1(tmp_path, capsys):
    rc = arch.main(["gone", "--save-dir", str(tmp_path), "--out-dir", str(tmp_path / "e")])
    assert rc == 1
    assert "归档失败" in capsys.readouterr().err
