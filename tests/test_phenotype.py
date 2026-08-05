"""B3 表型鉴定 harness + B4 一键组装链路（纯离线：mock HTTP / mock LLM）。"""

from __future__ import annotations

import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from yiagent import hof_pull
from yiagent.agent import AgentSession
from yiagent.cli.main import main
from yiagent.phenotype import (
    PhenotypeError,
    build_checklist,
    load_vector,
    render_checklist_md,
    run_live_smoke,
    smoke_checks,
    smoke_report,
)
from yiagent.recipient import import_genome, load_gene_source, save_vector

REPO = Path(__file__).resolve().parents[1]
FIXTURE_BANK = REPO / "factory" / "fixtures" / "alleles" / "bank.json"
DEMO_BANK = REPO / "demo" / "kepu" / "bank.json"
DEMO_VECTOR = REPO / "demo" / "kepu" / "vector_yg-seed-kepu01.json"
TS = "2026-08-01T00:00:00Z"  # 固定装配时间，保证产物可复现


def fixture_bank() -> dict:
    return json.loads(FIXTURE_BANK.read_text(encoding="utf-8"))


def champion_pack() -> dict:
    return import_genome(fixture_bank(), host="HOST", variant_id="var.champion", assembled_at=TS)


def demo_pack() -> dict:
    return json.loads(DEMO_VECTOR.read_text(encoding="utf-8"))


def check_map(report: dict) -> dict:
    return {c["name"]: c for c in report["checks"]}


class LoadVectorTests(unittest.TestCase):
    """vector 读入门禁：非装配产物一律拒绝。"""

    def test_load_ok(self):
        pack = load_vector(demo_pack())
        self.assertEqual(pack["kind"], "yiagent.expression_vector")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PhenotypeError):
                load_vector(Path(td) / "nope.json")

    def test_not_a_vector(self):
        with self.assertRaises(PhenotypeError):
            load_vector({"kind": "something else"})
        with self.assertRaises(PhenotypeError):
            load_vector({"kind": "yiagent.expression_vector"})  # 缺 markers/runtime


class SmokeOfflineTests(unittest.TestCase):
    """B3A offline 结构检查：正反例。"""

    def test_good_pack_all_ok(self):
        report = smoke_report(champion_pack())
        self.assertEqual(report["status"], "ok")
        checks = check_map(report)
        for name in (
            "smoke.pack_shape",
            "smoke.validation_ok",
            "smoke.g1_mounted",
            "smoke.g1_content",
            "smoke.g2_mounted",
            "smoke.g2_content",
            "smoke.g2_in_system",
            "smoke.skill_tools",
            "smoke.marker_line",
        ):
            self.assertTrue(checks[name]["ok"], name)

    def test_demo_pack_all_ok(self):
        report = smoke_report(demo_pack())
        self.assertEqual(report["status"], "ok")

    def test_g2_stripped_from_genome_text(self):
        """G2 边界被从基因组文本抹掉：g2_content / g2_in_system 双双失败。"""
        pack = champion_pack()
        pack["runtime"]["genome_system"] = pack["runtime"]["genome_system"].replace(
            "g2.persona.strict", "g2.persona.erased"
        )
        report = smoke_report(pack)
        self.assertEqual(report["status"], "fail")
        checks = check_map(report)
        self.assertFalse(checks["smoke.g2_content"]["ok"])
        self.assertFalse(checks["smoke.g2_in_system"]["ok"])

    def test_skill_tool_unmounted(self):
        """声明了工具却没挂载 = 能力清单不一致。"""
        pack = import_genome(None, host="HOST", variant_id="var.champion", assembled_at=TS)
        self.assertIn("notes_summary", pack["runtime"]["skill_tools"])
        pack["runtime"]["skill_tools"] = []
        checks = check_map(smoke_report(pack))
        self.assertFalse(checks["smoke.skill_tools"]["ok"])

    def test_gene_hash_erased_breaks_marker(self):
        pack = champion_pack()
        pack["markers"]["gene_hash"] = ""
        checks = check_map(smoke_report(pack))
        self.assertFalse(checks["smoke.pack_shape"]["ok"])
        self.assertFalse(checks["smoke.marker_line"]["ok"])


class ChecklistTests(unittest.TestCase):
    """B3B 规格对照 checklist：生成结构与越界核对。"""

    def test_demo_checklist_shape(self):
        cl = build_checklist(demo_pack())
        self.assertEqual(cl["kind"], "yiagent.phenotype_checklist")
        self.assertEqual(cl["spec"]["id"], "ai_科普")
        self.assertEqual(cl["gene_hash"], "yg-seed-kepu01")
        # 声明层 auto 全过；4 条「不做」留 live pending 由人打分
        self.assertEqual(cl["summary"]["auto_fail"], 0)
        self.assertEqual(cl["summary"]["live_pending"], 4)
        by_id = {i["id"]: i for i in cl["items"]}
        self.assertEqual(by_id["can.fact_check"]["status"], "pass")
        self.assertEqual(by_id["wont.advice"]["mode"], "live")
        self.assertEqual(by_id["wont.advice"]["status"], "pending")

    def test_render_md_table(self):
        md = render_checklist_md(build_checklist(demo_pack()))
        self.assertIn("| 项 | 侧 | 要求 | 方式 | 状态 | 备注 |", md)
        self.assertIn("can.knowledge_link", md)
        self.assertIn("boundary.web_tool", md)

    def test_undeclared_web_tool_flagged(self):
        """越界：联网工具未在基因盒声明却挂载，两条 boundary 都要拦。"""
        pack = demo_pack()
        pack["runtime"]["skill_tools"] = ["web_search"]
        by_id = {i["id"]: i for i in build_checklist(pack)["items"]}
        self.assertEqual(by_id["boundary.tools_declared"]["status"], "fail")
        # 基因组文本声明了「联网核对」，故 web_tool 项不判越界
        self.assertEqual(by_id["boundary.web_tool"]["status"], "pass")

    def test_web_tool_without_declaration_flagged(self):
        """基因组未声明联网却挂联网工具 = 越界能力。"""
        pack = demo_pack()
        pack["runtime"]["skill_tools"] = ["web_search"]
        # 工具改由某个基因盒「声明」（让 tools_declared 通过），单独探 web 越界
        pack["markers"]["skills"] = [{"id": "skill.fake_web", "tools": ["web_search"]}]
        pack["runtime"]["genome_system"] = pack["runtime"]["genome_system"].replace(
            "联网", "在册"
        )
        by_id = {i["id"]: i for i in build_checklist(pack)["items"]}
        self.assertEqual(by_id["boundary.tools_declared"]["status"], "pass")
        self.assertEqual(by_id["boundary.web_tool"]["status"], "fail")


class LiveGateTests(unittest.TestCase):
    """铁律：live 冒烟默认拒绝，代码路径上不存在自动实跑。"""

    def test_live_requires_confirmation(self):
        with self.assertRaises(PhenotypeError) as ctx:
            run_live_smoke(demo_pack(), prompt="hi", model="m")
        self.assertIn("人触发", str(ctx.exception))


class EndToEndTests(unittest.TestCase):
    """B4A 一键组装：hof pull → assemble → save_vector → session（全 mock/离线）。"""

    class _FakeResp:
        def __init__(self, payload: dict):
            self._raw = json.dumps(payload).encode("utf-8")

        def read(self) -> bytes:
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def test_pull_assemble_session_three_steps(self):
        payload = {"gene_hash": "yg-c94a8f01", "bank": fixture_bank()}
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            # 第 1 步：hof pull（HTTP mock）
            with patch.object(
                hof_pull.urllib.request, "urlopen", lambda *a, **k: self._FakeResp(payload)
            ):
                pulled = hof_pull.pull_genome("yg-c94a8f01", base_url="http://hof.test", home=home)
            self.assertTrue(pulled.is_file())
            # 第 2 步：assemble → save_vector（接入即校验 + B2C 能力核对）
            pack = import_genome(pulled, host="HOST", assembled_at=TS)
            self.assertEqual(pack["markers"]["source"]["kind"], "hof_pack")
            vector_path = save_vector(pack, Path(td) / "assembled")
            saved = load_vector(vector_path)
            # 第 3 步：session 直接消费装配产物（LLM mock）
            events: list[dict] = []

            def fake_chat(**_kw):
                return {
                    "choices": [{"message": {"role": "assistant", "content": "pong"}}],
                    "usage": {},
                }

            with patch("yiagent.agent.chat_completions", side_effect=fake_chat):
                sess = AgentSession(
                    model="kimi-k2.5",
                    api_key="sk-test-key-xxxxxxxx",
                    vector=saved,
                    cwd=td,
                    on_event=events.append,
                )
                out = sess.prompt("ping")
            self.assertEqual(out, "pong")
            # 可观测：genome_pack 事件带 marker_line，system 含基因组文本
            gp = [e for e in events if e.get("type") == "genome_pack"]
            self.assertTrue(gp)
            self.assertIn("yg-c94a8f01", gp[0]["line"])
            self.assertIn("g1.identity.v1", sess.messages[0]["content"])

    def test_vector_bad_kind_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                AgentSession(
                    model="m", api_key="k", vector={"kind": "nope"}, cwd=td
                )


class DemoPackageTests(unittest.TestCase):
    """B4B 演示包：样例 vector 过校验且可逐字节复现。"""

    def test_demo_vector_reproducible(self):
        saved = demo_pack()
        rebuilt = import_genome(
            DEMO_BANK,
            host=saved["runtime"]["host"],
            variant_id=saved["markers"]["variant_id"],
            assembled_at=saved["markers"]["assembled_at"],
        )
        self.assertEqual(rebuilt, saved)

    def test_demo_bank_intake_ok(self):
        src = load_gene_source(DEMO_BANK, variant_id="var.kepu_assistant")
        self.assertEqual(src.variant["hash"], "yg-seed-kepu01")
        report = smoke_report(demo_pack())
        self.assertEqual(report["status"], "ok")
        cl = build_checklist(demo_pack())
        self.assertEqual(cl["summary"]["auto_fail"], 0)


class CliSmokeTests(unittest.TestCase):
    """CLI：`yiagent smoke` offline 默认态 / `--vector` 直启 session。"""

    def _write_vector(self, td: str, pack: dict) -> Path:
        p = Path(td) / "vector.json"
        p.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        return p

    def test_cli_smoke_ok(self):
        with tempfile.TemporaryDirectory() as td:
            vp = self._write_vector(td, demo_pack())
            out, err = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                with redirect_stdout(out), redirect_stderr(err):
                    code = main(["smoke", str(vp)])
            self.assertEqual(code, 0)
            self.assertIn("status=ok", out.getvalue())
            self.assertIn("--live", err.getvalue())  # 默认提示：实跑由人触发

    def test_cli_smoke_bad_vector_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            vp = self._write_vector(td, {"kind": "nope"})
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = main(["smoke", str(vp)])
            self.assertEqual(code, 2)

    def test_cli_smoke_fail_exit_1(self):
        pack = demo_pack()
        pack["runtime"]["genome_system"] = "empty"
        with tempfile.TemporaryDirectory() as td:
            vp = self._write_vector(td, pack)
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = main(["smoke", str(vp)])
            self.assertEqual(code, 1)

    def test_cli_smoke_checklist_json(self):
        with tempfile.TemporaryDirectory() as td:
            vp = self._write_vector(td, demo_pack())
            out = io.StringIO()
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                with redirect_stdout(out), redirect_stderr(io.StringIO()):
                    code = main(["smoke", str(vp), "--checklist", "--json"])
            self.assertEqual(code, 0)
            # stdout 末尾是 checklist JSON（前面是 smoke 文本，取最后一个 JSON 块）
            text = out.getvalue()
            start = text.index('{\n  "kind": "yiagent.phenotype_checklist"')
            cl = json.loads(text[start:])
            self.assertEqual(cl["spec"]["id"], "ai_科普")

    def test_cli_run_with_vector(self):
        """`yiagent run --vector`：装配产物直启 one-shot（LLM mock）。"""
        with tempfile.TemporaryDirectory() as td:
            vp = self._write_vector(td, demo_pack())

            def fake_chat(**_kw):
                return {
                    "choices": [{"message": {"role": "assistant", "content": "答"}}],
                    "usage": {},
                }

            out = io.StringIO()
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                with patch("yiagent.agent.chat_completions", side_effect=fake_chat):
                    with redirect_stdout(out), redirect_stderr(io.StringIO()):
                        code = main(
                            ["run", "你好", "--vector", str(vp), "--api-key", "sk-test-x"]
                        )
            self.assertEqual(code, 0)
            self.assertIn("答", out.getvalue())


if __name__ == "__main__":
    unittest.main()
