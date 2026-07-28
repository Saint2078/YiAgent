"""Tests for genome assemble + cwd-scoped tools (no live LLM)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yiagent.agent import AgentSession
from yiagent.genome import (
    assemble_from_ids,
    assemble_system,
    get_variant,
    load_bank,
    load_skill,
    skill_openai_tools,
)
from yiagent.tools import dispatch, make_tools


class GenomeTests(unittest.TestCase):
    def test_default_bank_assemble(self):
        bank = load_bank()
        v = get_variant(bank, "var.champion")
        system = assemble_system("HOST", bank, v)
        self.assertIn("HOST", system)
        self.assertIn("g1.identity.v1", system)
        self.assertIn("装载纪律", system)
        self.assertIn("skill.workspace_notes", system)
        self.assertIn("g4.skill.notes.plan", system)

    def test_skill_cassette_definition(self):
        sk = load_skill("skill.workspace_notes")
        self.assertEqual(sk["kind"], "gene_cassette")
        self.assertTrue(sk["genes"]["G4"])
        self.assertTrue(sk["genes"]["G5"])
        tools = skill_openai_tools([sk])
        self.assertEqual(tools[0]["function"]["name"], "notes_summary")

    def test_assemble_from_ids_returns_skills(self):
        system, bank, variant, skills = assemble_from_ids(
            host="H", variant_id="var.champion"
        )
        self.assertIn("Skill · skill.workspace_notes", system)
        self.assertEqual(skills[0]["id"], "skill.workspace_notes")
        self.assertEqual(variant["id"], "var.champion")
        self.assertTrue(bank.get("variants"))


class ToolTests(unittest.TestCase):
    def test_read_write_edit_bash(self):
        with tempfile.TemporaryDirectory() as td:
            tools = make_tools(td)
            root = Path(td)
            (root / "a.txt").write_text("hello world\n", encoding="utf-8")
            out = dispatch(tools, "read", {"path": "a.txt"})
            self.assertIn("hello world", out)
            dispatch(tools, "edit", {"path": "a.txt", "old_string": "world", "new_string": "yiagent"})
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "hello yiagent\n")
            dispatch(tools, "write", {"path": "b.txt", "content": "x"})
            self.assertEqual((root / "b.txt").read_text(encoding="utf-8"), "x")
            bash_out = dispatch(tools, "bash", {"command": "echo ok"})
            self.assertIn("ok", bash_out)

    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as td:
            tools = make_tools(td)
            bad = dispatch(tools, "read", {"path": "../outside.txt"})
            self.assertTrue(bad.startswith("error:"))


class AgentLoopTests(unittest.TestCase):
    def test_tool_then_answer(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "note.txt").write_text("secret-42", encoding="utf-8")

            calls = {"n": 0}

            def fake_chat(**kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {
                                                "name": "read",
                                                "arguments": '{"path":"note.txt"}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ],
                        "usage": {},
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "The note says secret-42",
                            }
                        }
                    ],
                    "usage": {},
                }

            with patch("yiagent.agent.chat_completions", side_effect=fake_chat):
                sess = AgentSession(
                    model="kimi-k2.5",
                    api_key="sk-test-key-xxxxxxxx",
                    variant_id="var.champion",
                    cwd=td,
                )
                out = sess.prompt("What is in note.txt?")
            self.assertIn("secret-42", out)
            self.assertEqual(calls["n"], 2)
            roles = [m["role"] for m in sess.messages]
            self.assertIn("tool", roles)
            self.assertTrue(any(s["id"] == "skill.workspace_notes" for s in sess.skills))
            self.assertIn("notes_summary", sess.tools)


if __name__ == "__main__":
    unittest.main()
