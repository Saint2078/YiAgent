"""Session continue/resume tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yiagent import sessions as sesslib
from yiagent.cli.main import main


class SessionStoreTests(unittest.TestCase):
    def test_save_latest_resolve_title(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            with patch.dict(os.environ, {"YIAGENT_HOME": str(home)}, clear=False):
                rec = sesslib.create_record(
                    source="tui",
                    model="plan/k3",
                    variant_id="var.champion",
                    cwd=home / "workspace",
                    messages=[
                        {"role": "system", "content": "sys"},
                        {"role": "user", "content": "hello world session"},
                        {"role": "assistant", "content": "hi"},
                    ],
                    title="hello world session",
                )
                sesslib.save_session(rec, home)
                latest = sesslib.latest_session(source="tui", cwd=str((home / "workspace").resolve()), home=home)
                self.assertIsNotNone(latest)
                assert latest is not None
                self.assertEqual(latest["id"], rec["id"])
                by_title = sesslib.resolve_session("hello world session", home)
                self.assertEqual(by_title["id"], rec["id"])
                by_id = sesslib.resolve_session(rec["id"][:12], home)
                self.assertEqual(by_id["id"], rec["id"])

    def test_cli_sessions_list(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            with patch.dict(os.environ, {"YIAGENT_HOME": str(home)}, clear=False):
                self.assertEqual(main(["setup"]), 0)
                rec = sesslib.create_record(
                    source="tui",
                    model="plan/k3",
                    variant_id="var.champion",
                    cwd=home,
                    messages=[{"role": "user", "content": "x"}],
                    title="t0p session",
                )
                sesslib.save_session(rec, home)
                self.assertEqual(main(["sessions"]), 0)


if __name__ == "__main__":
    unittest.main()
