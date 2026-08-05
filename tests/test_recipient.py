"""B2 导入受体：基因来源接入 + 完整性校验 + 基因→可运行配置（纯离线）。"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yiagent.assembly import AssemblyBlocked, hash_format_ok, validate_genome
from yiagent.cli.main import main
from yiagent.genome import get_variant
from yiagent.improve_pack import KIND as IMPROVE_KIND
from yiagent.improve_pack import slot_texts_from_variant
from yiagent.recipient import (
    SOURCE_BANK,
    SOURCE_HOF_PACK,
    SOURCE_IMPROVE_PACK,
    capability_checks,
    import_genome,
    load_gene_source,
    save_vector,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURE_BANK = REPO / "factory" / "fixtures" / "alleles" / "bank.json"
TS = "2026-08-01T00:00:00Z"  # 固定装配时间，保证产物可复现


def fixture_bank() -> dict:
    return json.loads(FIXTURE_BANK.read_text(encoding="utf-8"))


def champion() -> dict:
    return copy.deepcopy(get_variant(fixture_bank(), "var.champion"))


def improve_pack_of(variant: dict) -> dict:
    """以 fixtures 冠军基因组构造 improve 导出包（与 export 同一形态）。"""
    bank = fixture_bank()
    return {
        "kind": IMPROVE_KIND,
        "version": 1,
        "seed": {
            "variant_id": variant["id"],
            "title": variant.get("title"),
            "hash": variant.get("hash"),
            "slots": dict(variant.get("slots") or {}),
            "slot_texts": slot_texts_from_variant(bank, variant),
        },
        "case": {"id": "case.t5", "title": "T5 导入受体"},
    }


class HashGateTests(unittest.TestCase):
    """B2A 严格 hash 门禁：只认名人堂规范 / sha256 / 种子白名单三种形态。"""

    def test_accepted_forms(self):
        self.assertTrue(hash_format_ok("yg-c94a8f01"))  # 名人堂规范 hash
        self.assertTrue(hash_format_ok("a" * 64))  # sha256 兜底形态
        self.assertTrue(hash_format_ok("yg-seed-ampion"))  # improve 种子库形态
        self.assertTrue(hash_format_ok("yg-seed-abc.DEF_1-2"))

    def test_rejected_forms(self):
        for bad in ("", "bad hash!!", "yg-c94a8f0", "yg-C94A8F01", "yg-seed-", "random"):
            self.assertFalse(hash_format_ok(bad), bad)


class SourceIntakeTests(unittest.TestCase):
    """B2A 来源接入：本地 bank / hof 落盘包 / improve 导出包统一收口。"""

    def test_local_bank_dict(self):
        src = load_gene_source(fixture_bank(), variant_id="var.champion")
        self.assertEqual(src.kind, SOURCE_BANK)
        self.assertEqual(src.variant["id"], "var.champion")

    def test_local_bank_path(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bank.json"
            p.write_text(json.dumps(fixture_bank(), ensure_ascii=False), encoding="utf-8")
            src = load_gene_source(p, variant_id="var.champion")
        self.assertEqual(src.kind, SOURCE_BANK)
        self.assertEqual(src.provenance.get("path"), str(p))

    def test_default_packaged_bank(self):
        """source=None 走默认打包 bank，也算本地 bank 来源。"""
        src = load_gene_source(None)
        self.assertEqual(src.kind, SOURCE_BANK)
        self.assertEqual(src.provenance.get("path"), "packaged:default_bank")
        self.assertTrue(src.variant.get("id"))

    def test_hof_pack_by_hash(self):
        """hof 落盘包：gene_hash + 内嵌 bank，默认按 hash 选基因组。"""
        pack = {"gene_hash": "yg-m55d1108", "bank": fixture_bank()}
        src = load_gene_source(pack)
        self.assertEqual(src.kind, SOURCE_HOF_PACK)
        self.assertEqual(src.variant["id"], "var.mid")
        self.assertEqual(src.provenance.get("gene_hash"), "yg-m55d1108")

    def test_hof_pack_variant_override(self):
        pack = {"gene_hash": "yg-c94a8f01", "bank": fixture_bank()}
        src = load_gene_source(pack, variant_id="var.champion")
        self.assertEqual(src.variant["id"], "var.champion")

    def test_improve_pack(self):
        """improve 导出包：seed 重建 bank（与 --apply 同一口径）后接入。"""
        src = load_gene_source(improve_pack_of(champion()))
        self.assertEqual(src.kind, SOURCE_IMPROVE_PACK)
        self.assertEqual(src.variant["hash"], "yg-c94a8f01")
        self.assertEqual(src.variant["slots"]["G1"], "g1.identity.v1")

    def test_best_genome_shape(self):
        """best_genome 形态（variant_id + slots + slot_texts）同样可接入。"""
        v = champion()
        best = {
            "variant_id": v["id"],
            "hash": v["hash"],
            "slots": dict(v["slots"]),
            "slot_texts": slot_texts_from_variant(fixture_bank(), v),
        }
        src = load_gene_source(best)
        self.assertEqual(src.kind, SOURCE_IMPROVE_PACK)

    def test_seed_default_hash_whitelisted(self):
        """improve 种子库缺省 hash（yg-seed-*）过白名单，不被门禁误杀。"""
        pack = improve_pack_of(champion())
        del pack["seed"]["hash"]  # bank_from_seed 兜底为 yg-seed-{vid 尾缀}
        src = load_gene_source(pack)
        self.assertTrue(src.variant["hash"].startswith("yg-seed-"))


class BadGenomeBlockedTests(unittest.TestCase):
    """铁律：残缺/坏基因一律 Blocked，禁止静默降级。"""

    def test_missing_file_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(AssemblyBlocked):
                load_gene_source(Path(td) / "nope.json")

    def test_invalid_json_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            with self.assertRaises(AssemblyBlocked):
                load_gene_source(p)

    def test_unrecognized_source_blocked(self):
        with self.assertRaises(AssemblyBlocked):
            load_gene_source({"foo": 1})

    def test_incomplete_bank_blocked(self):
        """hof 包缺完整 bank（alleles/variants）不得放行。"""
        with self.assertRaises(AssemblyBlocked):
            load_gene_source({"gene_hash": "yg-c94a8f01", "bank": {"alleles": {}}})

    def test_missing_required_slot_blocked_at_intake(self):
        """接入即校验：缺必需槽 G1 在 load_gene_source 阶段就 Blocked。"""
        bank = fixture_bank()
        v = champion()
        del v["slots"]["G1"]
        bank["variants"] = [v]
        with self.assertRaises(AssemblyBlocked) as ctx:
            load_gene_source(bank)
        self.assertTrue(any("G1" in e for e in ctx.exception.errors))

    def test_hof_pack_bad_hash_blocked(self):
        with self.assertRaises(AssemblyBlocked):
            load_gene_source({"gene_hash": "bad hash!!", "bank": fixture_bank()})

    def test_hof_pack_hash_mismatch_blocked(self):
        """包声明的 gene_hash 与基因组自带 hash 不一致 = 数据被换，Blocked。"""
        pack = {"gene_hash": "yg-c94a8f01", "bank": fixture_bank()}
        with self.assertRaises(AssemblyBlocked) as ctx:
            load_gene_source(pack, variant_id="var.mid")
        self.assertTrue(any("不一致" in e for e in ctx.exception.errors))

    def test_import_genome_blocked_writes_nothing(self):
        """坏基因不许出可运行配置：import_genome 抛错且不落盘。"""
        bank = fixture_bank()
        v = champion()
        v["slots"]["G4"] = "g4.cap.ghost"
        bank["variants"] = [v]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(AssemblyBlocked):
                import_genome(bank, host="HOST", assembled_at=TS)
            self.assertEqual(list(Path(td).rglob("*.json")), [])


class RunnableConfigTests(unittest.TestCase):
    """B2B 基因 → 可运行配置：三步显式可审计 + 落盘可复现。"""

    def test_import_genome_pack_shape(self):
        pack = import_genome(
            fixture_bank(), host="HOST", variant_id="var.champion", assembled_at=TS
        )
        self.assertEqual(pack["kind"], "yiagent.expression_vector")
        m = pack["markers"]
        self.assertEqual(m["gene_hash"], "yg-c94a8f01")
        self.assertEqual(m["source"]["kind"], SOURCE_BANK)  # 来源痕迹
        self.assertEqual(m["validation"]["status"], "ok")
        rt = pack["runtime"]
        self.assertIn("g1.identity.v1", rt["genome_system"])
        self.assertEqual(rt["host"], "HOST")

    def test_reproducible_save_roundtrip(self):
        """同一来源 + 固定时间戳 → 产物逐字节一致；落盘读回与内存一致。"""
        p1 = import_genome(fixture_bank(), host="HOST", variant_id="var.champion", assembled_at=TS)
        p2 = import_genome(fixture_bank(), host="HOST", variant_id="var.champion", assembled_at=TS)
        self.assertEqual(
            json.dumps(p1, ensure_ascii=False, sort_keys=True),
            json.dumps(p2, ensure_ascii=False, sort_keys=True),
        )
        with tempfile.TemporaryDirectory() as td:
            path = save_vector(p1, td)
            self.assertEqual(path.name, "vector_yg-c94a8f01.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), p1)

    def test_save_default_home_dir(self):
        """默认落盘 ~/.yiagent/assembled/（此处用临时 home 隔离）。"""
        pack = import_genome(fixture_bank(), host="HOST", variant_id="var.champion", assembled_at=TS)
        with tempfile.TemporaryDirectory() as td:
            path = save_vector(pack, home=Path(td))
            self.assertEqual(path.parent, Path(td) / "assembled")
            self.assertTrue(path.is_file())

    def test_three_step_audit_trail(self):
        """基因 → 配置 → 落盘三步各自显式：来源痕随配置包走。"""
        src = load_gene_source({"gene_hash": "yg-c94a8f01", "bank": fixture_bank()})
        pack = import_genome(
            {"gene_hash": "yg-c94a8f01", "bank": fixture_bank()},
            host="HOST",
            assembled_at=TS,
        )
        self.assertEqual(pack["markers"]["source"]["kind"], src.kind)
        self.assertEqual(pack["markers"]["source"]["gene_hash"], "yg-c94a8f01")
        with tempfile.TemporaryDirectory() as td:
            path = save_vector(pack, td)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["markers"]["source"]["kind"], SOURCE_HOF_PACK)


class CapabilityCheckTests(unittest.TestCase):
    """B2C 挂载清单核对：能力清单 ↔ 基因声明逐项对账。"""

    def test_checks_present_and_ok(self):
        """带 Skill 的基因组装配后，能力核对进 validation.checks 且通过。"""
        pack = import_genome(None, host="HOST", variant_id="var.champion", assembled_at=TS)
        checks = {c["name"]: c for c in pack["markers"]["validation"]["checks"]}
        self.assertTrue(checks["capability.tools_match"]["ok"])
        self.assertTrue(checks["capability.slot_mounts"]["ok"])
        self.assertIn("notes_summary", pack["runtime"]["skill_tools"])

    def test_tampered_tools_detected(self):
        """运行时工具清单被改 → 与基因声明不一致。"""
        pack = import_genome(None, host="HOST", variant_id="var.champion", assembled_at=TS)
        v = get_variant(fixture_bank(), "var.champion")
        self.assertTrue(all(c["ok"] for c in capability_checks(v, pack)))
        pack["runtime"]["skill_tools"] = []  # 篡改：工具没挂上
        bad = [c for c in capability_checks(v, pack) if not c["ok"]]
        self.assertEqual([c["name"] for c in bad], ["capability.tools_match"])

    def test_tampered_slot_mount_detected(self):
        pack = import_genome(fixture_bank(), host="HOST", variant_id="var.champion", assembled_at=TS)
        v = get_variant(fixture_bank(), "var.champion")
        pack["markers"]["slots"]["G3"]["allele_id"] = "g3.knowledge.ghost"
        bad = [c for c in capability_checks(v, pack) if not c["ok"]]
        # 篡改 markers 挂载点：与基因声明不符（slot_mounts），
        # 且该幽灵等位不在基因组文本里（genome_text，B2C 收尾新增）
        self.assertEqual(
            [c["name"] for c in bad],
            ["capability.slot_mounts", "capability.genome_text"],
        )

    def test_declared_skill_not_loaded_blocked(self):
        """基因声明了 Skill 却没装载 = 清单不一致，校验报告 blocked。"""
        bank = fixture_bank()
        v = champion()
        v["skills"] = ["skill.ghost"]
        report = validate_genome(bank, v, skills=[])
        self.assertEqual(report["status"], "blocked")
        names = {c["name"] for c in report["checks"]}
        self.assertIn("skill.skill.ghost.loaded", names)

    def test_import_genome_missing_skill_blocked(self):
        """声明的 Skill 文件不存在：导入直接 Blocked，不出配置。"""
        bank = fixture_bank()
        v = champion()
        v["skills"] = ["skill.ghost"]
        bank["variants"] = [v]
        with self.assertRaises(AssemblyBlocked):
            import_genome(bank, host="HOST", assembled_at=TS)


class CliAssembleTests(unittest.TestCase):
    """CLI 入口：`yiagent assemble` 只新增子命令，退出码区分成功/Blocked。"""

    def test_cli_assemble_ok(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "bank.json"
            src.write_text(json.dumps(fixture_bank(), ensure_ascii=False), encoding="utf-8")
            out = Path(td) / "out"
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                code = main(["assemble", str(src), "--variant", "var.champion", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue((out / "vector_yg-c94a8f01.json").is_file())

    def test_cli_assemble_blocked_exit_2(self):
        bank = fixture_bank()
        v = champion()
        del v["slots"]["G2"]
        bank["variants"] = [v]
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "bad.json"
            src.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")
            with patch.dict(os.environ, {"YIAGENT_HOME": str(Path(td) / "home")}, clear=False):
                code = main(["assemble", str(src)])
            self.assertEqual(code, 2)
            self.assertEqual(list(Path(td).rglob("vector_*.json")), [])


if __name__ == "__main__":
    unittest.main()
