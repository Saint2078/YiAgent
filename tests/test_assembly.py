"""B1 表达载体装配：分槽规则 + 配置包 + 可观测标记（纯离线）。"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from yiagent.agent import AgentSession
from yiagent.assembly import (
    PACK_KIND,
    SLOT_RULES,
    AssemblyBlocked,
    assemble_vector,
    gene_hash_of,
    marker_line,
    validate_genome,
)
from yiagent.genome import get_variant, load_bank

REPO = Path(__file__).resolve().parents[1]
FIXTURE_BANK = REPO / "factory" / "fixtures" / "alleles" / "bank.json"
TS = "2026-08-01T00:00:00Z"  # 固定装配时间，保证产物可复现


def fixture_bank() -> dict:
    return json.loads(FIXTURE_BANK.read_text(encoding="utf-8"))


class SlotRuleTests(unittest.TestCase):
    def test_rules_cover_all_slots(self):
        self.assertEqual(tuple(SLOT_RULES), ("G1", "G2", "G3", "G4", "G5"))
        # G1/G2 为骨架必需槽；G3–G5 可缺省且允许 Skill 注入
        self.assertTrue(SLOT_RULES["G1"].required)
        self.assertTrue(SLOT_RULES["G2"].required)
        for s in ("G3", "G4", "G5"):
            self.assertFalse(SLOT_RULES[s].required)
            self.assertEqual(SLOT_RULES[s].on_missing, "default_skip")
            self.assertTrue(SLOT_RULES[s].allow_skill)


class AssembleSmokeTests(unittest.TestCase):
    def test_fixture_bank_champion(self):
        """冒烟：fixtures 既有等位/基因组样例正常装配。"""
        pack = assemble_vector(
            "HOST", bank=FIXTURE_BANK, variant_id="var.champion", assembled_at=TS
        )
        self.assertEqual(pack["kind"], PACK_KIND)
        m = pack["markers"]
        self.assertEqual(m["gene_hash"], "yg-c94a8f01")
        self.assertEqual(m["variant_id"], "var.champion")
        self.assertEqual(m["assembled_at"], TS)
        self.assertEqual(m["validation"]["status"], "ok")
        for s in ("G1", "G2", "G3", "G4", "G5"):
            self.assertEqual(m["slots"][s]["state"], "mounted")
            self.assertTrue(m["slots"][s]["allele_id"])
        self.assertEqual(m["slots"]["G1"]["version"], "v1")
        # 运行时配置：基因组文本与挂载点
        rt = pack["runtime"]
        self.assertIn("g1.identity.v1", rt["genome_system"])
        self.assertIn("HOST", rt["genome_system"])
        self.assertEqual(rt["slot_mounts"]["G4"], "system.genome#G4")
        # 配置包整体必须可 JSON 序列化（可落盘审计）
        json.dumps(pack, ensure_ascii=False)

    def test_default_bank_skill_markers(self):
        pack = assemble_vector("HOST", variant_id="var.champion", assembled_at=TS)
        sk = pack["markers"]["skills"]
        self.assertEqual(sk[0]["id"], "skill.workspace_notes")
        self.assertIn("notes_summary", pack["runtime"]["skill_tools"])

    def test_reproducible(self):
        """同一基因组 + 固定时间戳 → 配置包逐字节一致。"""
        p1 = assemble_vector("HOST", bank=FIXTURE_BANK, variant_id="var.mid", assembled_at=TS)
        p2 = assemble_vector("HOST", bank=FIXTURE_BANK, variant_id="var.mid", assembled_at=TS)
        self.assertEqual(
            json.dumps(p1, ensure_ascii=False, sort_keys=True),
            json.dumps(p2, ensure_ascii=False, sort_keys=True),
        )

    def test_marker_line(self):
        pack = assemble_vector("HOST", bank=FIXTURE_BANK, variant_id="var.champion", assembled_at=TS)
        line = marker_line(pack)
        self.assertIn("gene_hash=yg-c94a8f01", line)
        self.assertIn("variant=var.champion", line)
        self.assertIn("G4:g4.cap.structured", line)
        self.assertIn("status=ok", line)


class DefaultSkipTests(unittest.TestCase):
    def test_optional_slot_missing_goes_default(self):
        """缺可选槽（G5）走缺省：装配通过并在标记中留痕。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        del v["slots"]["G5"]
        pack = assemble_vector("HOST", bank=bank, variant=v, assembled_at=TS)
        g5 = pack["markers"]["slots"]["G5"]
        self.assertEqual(g5["state"], "default_skip")
        self.assertIsNone(g5["allele_id"])
        self.assertEqual(pack["markers"]["validation"]["status"], "ok")
        self.assertIn("g1.identity.v1", pack["runtime"]["genome_system"])

    def test_hash_fallback_computed(self):
        """缺 hash 字段不算坏基因：按 slots 计算 sha256 兜底。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        del v["hash"]
        pack = assemble_vector("HOST", bank=bank, variant=v, assembled_at=TS)
        gh = pack["markers"]["gene_hash"]
        self.assertEqual(len(gh), 64)
        self.assertEqual(gh, gene_hash_of(v))


class BlockedTests(unittest.TestCase):
    def test_missing_required_slot_blocked(self):
        """缺必需槽（G1 身份 / G2 硬边界）必须 Blocked。"""
        bank = fixture_bank()
        for slot in ("G1", "G2"):
            v = copy.deepcopy(get_variant(bank, "var.champion"))
            del v["slots"][slot]
            with self.assertRaises(AssemblyBlocked) as ctx:
                assemble_vector("HOST", bank=bank, variant=v)
            self.assertTrue(any(slot in e for e in ctx.exception.errors))

    def test_unknown_allele_blocked(self):
        """坏基因：槽位引用了 bank 中不存在的等位。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        v["slots"]["G3"] = "g3.knowledge.ghost"
        with self.assertRaises(AssemblyBlocked) as ctx:
            assemble_vector("HOST", bank=bank, variant=v)
        self.assertTrue(any("g3.knowledge.ghost" in e for e in ctx.exception.errors))

    def test_allele_missing_text_blocked(self):
        """坏基因：等位缺 text 字段。"""
        bank = fixture_bank()
        bank["alleles"]["G3"].append({"id": "g3.knowledge.empty", "label": "空壳"})
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        v["slots"]["G3"] = "g3.knowledge.empty"
        with self.assertRaises(AssemblyBlocked):
            assemble_vector("HOST", bank=bank, variant=v)

    def test_bad_hash_blocked(self):
        """坏 hash：含空白/非法字符的 hash 字段被拒绝。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        v["hash"] = "bad hash!!"
        with self.assertRaises(AssemblyBlocked) as ctx:
            assemble_vector("HOST", bank=bank, variant=v)
        self.assertTrue(any("hash" in e for e in ctx.exception.errors))

    def test_unknown_variant_blocked(self):
        with self.assertRaises(AssemblyBlocked):
            assemble_vector("HOST", bank=FIXTURE_BANK, variant_id="var.ghost")

    def test_empty_bank_blocked(self):
        """无基因不组装：bank 无任何 variant 直接 Blocked。"""
        with self.assertRaises(AssemblyBlocked):
            assemble_vector("HOST", bank={"alleles": {}, "variants": []})

    def test_skill_scope_violation_blocked(self):
        """Skill 试图注入 G1/G2 受限槽 → Blocked。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        evil = {
            "id": "skill.evil",
            "genes": {"G1": [{"id": "g1.fake", "text": "改写身份"}]},
            "tools": [],
        }
        with self.assertRaises(AssemblyBlocked):
            assemble_vector("HOST", bank=bank, variant=v, skills=[evil])


class ValidateHookTests(unittest.TestCase):
    def test_validate_returns_report_without_raising(self):
        """校验钩子：返回结构化报告，不抛异常（B2A 挂接位）。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        del v["slots"]["G1"]
        v["hash"] = "bad hash!!"
        report = validate_genome(bank, v)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["errors"])
        names = {c["name"] for c in report["checks"]}
        self.assertIn("G1.present", names)
        self.assertIn("hash_format", names)


class SessionPackTests(unittest.TestCase):
    def test_session_carries_pack_and_event(self):
        """运行时状态可读：session 挂配置包并发出 genome_pack 事件。"""
        events: list[dict] = []
        with tempfile.TemporaryDirectory() as td:
            sess = AgentSession(
                model="kimi-k2.5",
                api_key="sk-test-key-xxxxxxxx",
                variant_id="var.champion",
                cwd=td,
                on_event=events.append,
            )
        self.assertIsNotNone(sess.genome_pack)
        self.assertEqual(sess.genome_pack["markers"]["validation"]["status"], "ok")
        hit = [e for e in events if e.get("type") == "genome_pack"]
        self.assertTrue(hit)
        self.assertIn("gene_hash=yg-c94a8f01", hit[0]["line"])

    def test_session_blocked_on_bad_genome(self):
        """坏基因不许硬组装：session 构造即 AssemblyBlocked。"""
        bank = fixture_bank()
        v = copy.deepcopy(get_variant(bank, "var.champion"))
        v["slots"]["G4"] = "g4.cap.ghost"
        bank["variants"] = [v]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(AssemblyBlocked):
                AgentSession(
                    model="kimi-k2.5",
                    api_key="sk-test-key-xxxxxxxx",
                    variant_id="var.champion",
                    bank=bank,
                    cwd=td,
                )


if __name__ == "__main__":
    unittest.main()
