"""Tests for Runtime + AGENTS.md layers (not genome)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yiagent.context_files import find_agents_md, load_agents_md
from yiagent.genome import assemble_system, get_variant, load_bank
from yiagent.prompt_layers import compose_system
from yiagent.runtime_rules import load_runtime_rules, rules_path


class LayerTests(unittest.TestCase):
    def test_genome_excludes_runtime(self):
        bank = load_bank()
        v = get_variant(bank, "var.champion")
        genome = assemble_system("HOST", bank, v)
        self.assertIn("HOST", genome)
        self.assertIn("g1.identity.v1", genome)
        self.assertNotIn("Runtime rules", genome)
        self.assertNotIn("装载优先级", genome)

    def test_compose_adds_runtime_and_agents(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            home.mkdir()
            cwd = Path(td) / "proj"
            cwd.mkdir()
            (cwd / "AGENTS.md").write_text("# Project\nuse poetry\n", encoding="utf-8")
            (home / "RULES.md").write_text("never sudo\n", encoding="utf-8")
            with patch.dict(os.environ, {"YIAGENT_HOME": str(home)}, clear=False):
                full = compose_system(
                    "GENOME_BODY",
                    cwd=cwd,
                    home=home,
                    cfg={"runtime": {"rules": True, "rules_file": True}, "context": {"agents_md": True}},
                )
            self.assertIn("GENOME_BODY", full)
            self.assertIn("G2 硬边界", full)
            self.assertIn("Runtime rules", full)
            self.assertIn("never sudo", full)
            self.assertIn("AGENTS.md", full)
            self.assertIn("use poetry", full)

    def test_agents_walk_parents(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "AGENTS.md").write_text("root-agents", encoding="utf-8")
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            found = find_agents_md(nested)
            self.assertEqual(found, root / "AGENTS.md")
            self.assertIn("root-agents", load_agents_md(nested))

    def test_rules_path(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            self.assertEqual(rules_path(home), home / "RULES.md")
            text = load_runtime_rules(home=home, cfg={"runtime": {"rules": False, "rules_file": False}})
            self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
