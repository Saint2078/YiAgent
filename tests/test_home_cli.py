"""Tests for Hermes-style home/config (no live LLM)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yiagent.config_store import bootstrap_home, load_config, load_dotenv_file, save_config, set_nested
from yiagent.cli.doctor import run_doctor
from yiagent.cli.main import main


class HomeConfigTests(unittest.TestCase):
    def test_bootstrap_and_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            with patch.dict(os.environ, {"YIAGENT_HOME": str(home)}, clear=False):
                bootstrap_home(home)
                self.assertTrue((home / "config.yaml").is_file())
                self.assertTrue((home / ".env").is_file())
                cfg = load_config(home)
                self.assertEqual(cfg["model"]["default"], "plan/k3")
                set_nested(cfg, "agent.variant", "var.soft_champion")
                save_config(cfg, home)
                again = load_config(home)
                self.assertEqual(again["agent"]["variant"], "var.soft_champion")

    def test_dotenv_load(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("MOONSHOT_API_KEY=sk-test-abcdef\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("MOONSHOT_API_KEY", None)
                load_dotenv_file(env, override=True)
                self.assertEqual(os.environ.get("MOONSHOT_API_KEY"), "sk-test-abcdef")

    def test_cli_variants_and_doctor(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            with patch.dict(os.environ, {"YIAGENT_HOME": str(home)}, clear=False):
                self.assertEqual(main(["setup"]), 0)
                # doctor fails without API key — still runnable
                code = run_doctor(fix=False)
                self.assertIn(code, (0, 1))
                self.assertEqual(main(["variants"]), 0)


if __name__ == "__main__":
    unittest.main()
