"""工厂实跑冠军 → 表达载体：血统随载体走 + 泛化门禁（纯离线）。

守两件事，否则以后会被无声改掉：

1. rolefactory 导出的 bank 装出来的载体，`markers.provenance` 必须在，
   且 `marker_line` 一眼能看出能不能宣称更强；
2. `--require-generalization` 只放行**已证明**的（`generalizes is True`），
   「判不了」（None）不许被当成好消息放过去。
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from yiagent.assembly import assemble_vector, generalizes, marker_line
from yiagent.recipient import import_genome, provenance_path

REPO = Path(__file__).resolve().parents[1]
TS = "2026-08-01T00:00:00Z"

# 最小可装配 bank：结构照 rolefactory 导出物（含 meta.provenance），不依赖实跑数据
def _bank(verdict: dict | None) -> dict:
    provenance = {
        "factory": "rolefactory",
        "run_id": "20260101-000000-testid",
        "role": "测试席位",
        "genome_hash": "a" * 64,
        "champion_weighted": 80.0,
        "baseline_weighted": 70.0,
        "delta_train_weighted": 10.0,
        "holdout": {"source": "run", "reps": 1, "delta_weighted": -1.0},
        "verdict": verdict or {},
        "claim": "测试用",
    }
    return {
        "meta": {"role_id": "role_test", "display_name": "测试席位", "provenance": provenance},
        "alleles": {
            slot: [{"id": f"{slot.lower()}_a", "label": f"{slot} 强", "text": f"{slot} 文本"}]
            for slot in ("G1", "G2", "G3", "G4", "G5")
        },
        "variants": [
            {
                "id": "var.role_test.champion",
                "hash": "a" * 64,
                "title": "测试冠军",
                "slots": {s: f"{s.lower()}_a" for s in ("G1", "G2", "G3", "G4", "G5")},
            }
        ],
    }


class ProvenanceTests(unittest.TestCase):
    def test_provenance_rides_along(self):
        pack = assemble_vector("host", _bank({"generalizes": None, "label": "判不了"}), assembled_at=TS)
        pr = pack["markers"]["provenance"]
        self.assertEqual(pr["run_id"], "20260101-000000-testid")
        self.assertEqual(pr["genome_hash"], "a" * 64)
        # 载体的 gene_hash 与工厂基因组卡同一套哈希 → 可回溯实跑
        self.assertEqual(pack["markers"]["gene_hash"], "a" * 64)

    def test_no_provenance_key_when_bank_has_none(self):
        # 没血统的 bank 不许凭空造这个键：否则既有演示载体字节会变，逐字节复现失效
        bank = _bank(None)
        bank["meta"].pop("provenance")
        pack = assemble_vector("host", bank, assembled_at=TS)
        self.assertNotIn("provenance", pack["markers"])
        self.assertNotIn("generalizes=", marker_line(pack))

    def test_variant_provenance_overrides_bank(self):
        # 对照件不许继承冠军的战绩：variant 自带血统优先
        bank = _bank({"generalizes": True, "label": "站得住"})
        bank["variants"].append(
            {
                "id": "var.role_test.all_weak",
                "title": "全弱对照",
                "slots": {s: f"{s.lower()}_a" for s in ("G1", "G2", "G3", "G4", "G5")},
                "provenance": {"kind": "contrast_all_weak", "claim": "仅作对照",
                               "verdict": {"generalizes": None, "label": "对照件（不参与判定）"}},
            }
        )
        champ = assemble_vector("host", bank, variant_id="var.role_test.champion", assembled_at=TS)
        weak = assemble_vector("host", bank, variant_id="var.role_test.all_weak", assembled_at=TS)
        self.assertIs(generalizes(champ), True)
        self.assertIsNone(generalizes(weak))
        self.assertEqual(weak["markers"]["provenance"]["claim"], "仅作对照")

    def test_marker_line_shows_verdict(self):
        pack = assemble_vector("host", _bank({"generalizes": None, "label": "reps=1 判不了"}), assembled_at=TS)
        line = marker_line(pack)
        self.assertIn("generalizes=None", line)
        self.assertIn("reps=1 判不了", line)


class GeneralizesTests(unittest.TestCase):
    def test_三态(self):
        for raw, want in ((True, True), (False, False), (None, None)):
            pack = assemble_vector("host", _bank({"generalizes": raw}), assembled_at=TS)
            self.assertIs(generalizes(pack), want)

    def test_missing_provenance_is_none(self):
        self.assertIsNone(generalizes({"markers": {}}))

    def test_non_bool_verdict_is_none(self):
        # 判定字段写成字符串 "true" 之类，不许当成已证明
        pack = assemble_vector("host", _bank({"generalizes": "true"}), assembled_at=TS)
        self.assertIsNone(generalizes(pack))


class GateCliTests(unittest.TestCase):
    """`yiagent assemble --require-generalization` 的放行/拒装。"""

    def _run(self, bank: dict, *extra: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "bank.json"
            src.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")
            env = {
                **__import__("os").environ,
                "PYTHONPATH": str(REPO / "src"),
                "PYTHONIOENCODING": "utf-8",
                "YIAGENT_HOME": str(Path(td) / "home"),
            }
            return subprocess.run(
                [sys.executable, "-m", "yiagent.cli.main", "assemble", str(src),
                 "--variant", "var.role_test.champion", "--out", str(Path(td) / "out"), *extra],
                capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(REPO),
            )

    def test_gate_blocks_inconclusive(self):
        r = self._run(_bank({"generalizes": None, "label": "判不了"}), "--require-generalization")
        self.assertEqual(r.returncode, 3)
        self.assertIn("泛化未证明", r.stderr)

    def test_gate_blocks_refuted(self):
        r = self._run(_bank({"generalizes": False, "label": "过拟合"}), "--require-generalization")
        self.assertEqual(r.returncode, 3)

    def test_gate_passes_proven(self):
        r = self._run(_bank({"generalizes": True, "label": "站得住"}), "--require-generalization")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("saved:", r.stdout)

    def test_default_assembles_but_stamps(self):
        # 默认放行，但必须把「不得宣称更强」印在输出里
        r = self._run(_bank({"generalizes": None, "label": "判不了"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("可宣称", r.stdout)
        self.assertIn("判不了", r.stdout)


class ProvenancePathTests(unittest.TestCase):
    """来源路径可移植：仓库内记 repo: 相对路径，跨机器逐字节复现。"""

    def test_repo_relative(self):
        p = provenance_path(REPO / "demo" / "kepu" / "bank.json")
        self.assertEqual(p, "repo:demo/kepu/bank.json")

    def test_outside_repo_stays_absolute(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "bank.json"
            f.write_text("{}", encoding="utf-8")
            self.assertNotIn("repo:", provenance_path(f))

    def test_demo_vector_has_portable_path(self):
        saved = json.loads(
            (REPO / "demo" / "kepu" / "vector_yg-seed-kepu01.json").read_text(encoding="utf-8")
        )
        path = saved["markers"]["source"]["path"]
        self.assertEqual(path, "repo:demo/kepu/bank.json")
        # 落盘产物里不许出现机器绝对路径
        self.assertNotIn(":\\", path)
        self.assertFalse(path.startswith("/"))


class ExportedBankShapeTests(unittest.TestCase):
    """实跑导出的六席 bank（若在本机）确实可装配，且带血统。"""

    BANKS = REPO / "rolefactory" / "data" / "yiagent_banks"

    def test_exported_banks_assemble(self):
        banks = sorted(self.BANKS.glob("*.bank.json")) if self.BANKS.is_dir() else []
        if not banks:
            self.skipTest(
                f"本机没有导出的实跑 bank（{self.BANKS} 为运行时产物）；"
                "跑 rolefactory/tools/export_yiagent_bank.py --all 后本用例生效"
            )
        for path in banks:
            with self.subTest(bank=path.name):
                bank = json.loads(path.read_text(encoding="utf-8"))
                champion = next(
                    v for v in bank["variants"] if v.get("role_in_pack") == "champion"
                )
                pack = import_genome(path, host="host", variant_id=champion["id"], assembled_at=TS)
                pr = pack["markers"]["provenance"]
                self.assertTrue(pr.get("run_id"))
                self.assertTrue(pr.get("claim"))
                # 冠军 hash 必须是规范 64 位 sha256，才能回溯基因组卡
                self.assertRegex(pack["markers"]["gene_hash"], r"^[0-9a-f]{64}$")
                # 没证明更强的，claim 里不许出现「已验证」
                if generalizes(pack) is not True:
                    self.assertNotIn("已验证更强", pr["claim"].replace("不可称『已验证更强』", ""))


class EntityReproducibleTests(unittest.TestCase):
    """落盘的六席载体必须能由基因库逐字节重建（跨机器、跨时间）。"""

    SEAT_DIR = REPO / "console" / "_workbench" / "AgentTeam" / "Develop"
    BANKS = REPO / "rolefactory" / "data" / "yiagent_banks"

    def test_saved_vectors_rebuild_identically(self):
        pairs = [
            (seat.name, seat / "vector.json", self.BANKS / f"{seat.name}.bank.json")
            for seat in sorted(self.SEAT_DIR.glob("*"))
            if (seat / "vector.json").is_file() and (self.BANKS / f"{seat.name}.bank.json").is_file()
        ] if self.SEAT_DIR.is_dir() else []
        if not pairs:
            self.skipTest("本机没有落盘载体（运行时产物）；跑 scripts/build_agent_entities.py 后生效")

        sys.path.insert(0, str(REPO / "scripts"))
        from build_agent_entities import HOST, _fixed_stamp  # noqa: PLC0415

        for seat, vpath, bpath in pairs:
            with self.subTest(seat=seat):
                saved = json.loads(vpath.read_text(encoding="utf-8"))
                bank = json.loads(bpath.read_text(encoding="utf-8"))
                rebuilt = import_genome(
                    bpath, host=HOST,
                    variant_id=saved["markers"]["variant_id"],
                    assembled_at=_fixed_stamp(bank),
                )
                # source.path 是本机相对仓库根的写法，两侧都走同一函数，应完全相等
                self.assertEqual(rebuilt, saved, f"{seat} 载体无法逐字节重建")

    def test_reexport_does_not_change_bytes(self):
        """强口径：**重新导出基因库**后载体仍逐字节一致。

        弱口径（给定同一份 bank 可重建）挡不住一个 `exported_at` ——
        导出时刻泄进产物，交付物就不再是「这次实跑」的纯函数了。
        """
        exporter = REPO / "rolefactory" / "tools" / "export_yiagent_bank.py"
        banks = sorted((REPO / "rolefactory" / "data" / "yiagent_banks").glob("*.bank.json"))
        if not banks or not exporter.is_file():
            self.skipTest("本机没有导出的实跑 bank")

        import os  # noqa: PLC0415

        seat = banks[0].stem.replace(".bank", "")
        before = banks[0].read_bytes()
        r = subprocess.run(
            [sys.executable, str(exporter), "--seat", seat],
            cwd=str(REPO / "rolefactory"), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            banks[0].read_bytes(), before,
            f"{seat} 基因库重新导出后字节变了：交付物不是实跑的纯函数",
        )

    def test_stamp_anchored_on_run_not_export(self):
        # 装配时间必须锚在实跑时刻：否则重新导出基因库就换字节，「可复现」名存实亡
        sys.path.insert(0, str(REPO / "scripts"))
        from build_agent_entities import _fixed_stamp  # noqa: PLC0415

        bank = {"meta": {"provenance": {"run_at": "2026-01-01T00:00:00Z",
                                        "exported_at": "2026-08-11T03:00:00+00:00"}}}
        self.assertEqual(_fixed_stamp(bank), "2026-01-01T00:00:00Z")
        # 旧 bank 没有 run_at 时退回导出时刻，而不是 now()
        old = {"meta": {"provenance": {"exported_at": "2026-08-11T03:00:00+00:00"}}}
        self.assertEqual(_fixed_stamp(old), "2026-08-11T03:00:00Z")


class EntityBootsTests(unittest.TestCase):
    """六席载体必须真能启动成 Agent —— 不只是「存在一个 JSON」。

    LLM 全 mock，一次真实调用都不发；验的是「载体 → 可对话会话」这一步接得上：
    基因组文本确实进了 system、身份等位在里面、`genome_pack` 事件带得出判定。
    """

    SEAT_DIR = REPO / "console" / "_workbench" / "AgentTeam" / "Develop"

    def test_every_seat_boots_a_session(self):
        from unittest.mock import patch  # noqa: PLC0415

        from yiagent.agent import AgentSession  # noqa: PLC0415
        from yiagent.phenotype import load_vector  # noqa: PLC0415

        vectors = sorted(self.SEAT_DIR.glob("*/vector.json")) if self.SEAT_DIR.is_dir() else []
        if not vectors:
            self.skipTest("本机没有落盘载体；跑 scripts/build_agent_entities.py 后生效")

        def fake_chat(**_kw):
            return {"choices": [{"message": {"role": "assistant", "content": "pong"}}], "usage": {}}

        for vpath in vectors:
            seat = vpath.parent.name
            with self.subTest(seat=seat):
                pack = load_vector(vpath)
                events: list[dict] = []
                with tempfile.TemporaryDirectory() as td, \
                     patch("yiagent.agent.chat_completions", side_effect=fake_chat):
                    sess = AgentSession(
                        model="kimi-k2.5", api_key="sk-test-key-xxxxxxxx",
                        vector=pack, cwd=td, on_event=events.append,
                    )
                    self.assertEqual(sess.prompt("ping"), "pong")

                system = sess.messages[0]["content"]
                # G1/G2 的等位 id 必须真出现在 system 里，否则基因等于没装上
                for slot in ("G1", "G2"):
                    aid = pack["markers"]["slots"][slot]["allele_id"]
                    self.assertIn(aid, system, f"{seat} 的 {slot} 等位 {aid} 没进 system")
                # 构造即发 genome_pack 事件，且这一行带着泛化判定（能不能宣称更强）
                gp = [e for e in events if e.get("type") == "genome_pack"]
                self.assertTrue(gp, f"{seat} 没发 genome_pack 事件")
                self.assertIn("generalizes=", gp[0]["line"])


if __name__ == "__main__":
    unittest.main()
