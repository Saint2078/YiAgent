"""凭证扫描器的测试：**两个方向都必须钉住**。

- 漏报（该拦没拦）比没有扫描更糟：它给人"扫过了所以安全"的错觉。
- 误报（不该拦却拦）会让人加 `--no-verify`，两次之后钩子就被删掉，
  于是扫描变成纯粹的心理安慰。

所以正例和反例一样多。

用法：python -m tests.test_scan_secrets
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "hooks"))

import scan_secrets as ss  # noqa: E402


class ShouldCatchTests(unittest.TestCase):
    """真凭证形态必须被拦下。"""

    def _hit(self, text: str) -> bool:
        return bool(ss.scan_text(text))

    def test_openai_style_key(self):
        self.assertTrue(self._hit('KEY = "sk-abcdef0123456789abcdef0123"'))  # allowlist secret

    def test_moonshot_style_key_in_json(self):
        self.assertTrue(self._hit('{"apiKey": "sk-9f8e7d6c5b4a39281706abcd"}'))  # allowlist secret

    def test_aws_access_key(self):
        self.assertTrue(self._hit("AWS_ID=AKIAIOSFODNN7EXAMPLE"))  # allowlist secret

    def test_github_token(self):
        self.assertTrue(self._hit("token: ghp_16CharsAndMore0123456789abcdefghij"))  # allowlist secret

    def test_bearer_header(self):
        self.assertTrue(self._hit(
            'h["Authorization"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6"'))  # allowlist secret

    def test_private_key_header(self):
        self.assertTrue(self._hit("-----BEGIN RSA PRIVATE KEY-----"))  # allowlist secret

    def test_hardcoded_assignment(self):
        self.assertTrue(self._hit('password = "Xk92mfQ0zLp47vBn"'))  # allowlist secret

    def test_masks_the_value_instead_of_printing_it(self):
        """报告里不能把凭证原文再打一遍 —— 那等于换个地方泄露。"""
        hits = ss.scan_text('KEY = "sk-abcdef0123456789abcdef0123"')  # allowlist secret
        _, _, masked = hits[0]
        self.assertNotIn("abcdef0123456789", masked)
        self.assertIn("…", masked)


class AllowlistTests(unittest.TestCase):
    """豁免标记：钩子第一次真用就拦下了本文件，这个机制是那次的产物。

    要求两条：标了的那一行放行；**没标的行不受影响**（否则一个标记就等于关掉整个文件）。
    """

    def test_marked_line_is_skipped(self):
        self.assertEqual(
            ss.scan_text('KEY = "sk-abcdef0123456789abcdef0123"  # allowlist secret'), []
        )

    def test_pragma_form_also_works(self):
        self.assertEqual(
            ss.scan_text('KEY = "sk-abcdef0123456789abcdef0123"  # pragma: allowlist secret'), []
        )

    def test_marker_does_not_leak_to_other_lines(self):
        """标记只豁免它所在的那一行 —— 否则等于整文件豁免，会随时间腐化。

        第二行**故意不加标记**，所以它不能以字面形式出现在本文件里
        （否则下一条"本文件必须干净"就会被它自己绊倒 —— 实测绊过一次）。
        用拼接构造：运行时是完整密钥，源码里没有可匹配的字面串。
        """
        key = "sk-" + "9f8e7d6c5b4a39281706abcd"
        text = (
            'a = "sk-abcdef0123456789abcdef0123"  # allowlist secret\n'  # allowlist secret
            f'b = "{key}"\n'
        )
        hits = ss.scan_text(text)
        self.assertEqual(len(hits), 1, "标记影响了别的行")
        self.assertEqual(hits[0][0], 2, "豁免了错误的行")

    def test_scanner_self_test_file_is_clean_as_a_file(self):
        """本文件必须能过文件级扫描 —— 否则每次改它都要 --no-verify。"""
        self.assertEqual(ss.scan_file(Path(__file__)), [])


class ShouldNotCatchTests(unittest.TestCase):
    """误报会让钩子被删掉，所以这些都必须放行。"""

    def _hit(self, text: str) -> bool:
        return bool(ss.scan_text(text))

    def test_env_read_is_fine(self):
        self.assertFalse(self._hit('api_key = os.environ["MOONSHOT_API_KEY"]'))

    def test_dotenv_style_reference(self):
        self.assertFalse(self._hit('const key = process.env.OPENAI_API_KEY;'))

    def test_powershell_env_read(self):
        self.assertFalse(self._hit('$key = $env:KIMI_API_KEY'))

    def test_word_without_value(self):
        self.assertFalse(self._hit("# 配置项：api_key 从环境变量读，不写在仓里"))

    def test_placeholder_values(self):
        for v in ("${API_KEY}", "your-api-key-here", "xxxxxxxxxxxxxxxx",
                  "changeme-please-now", "placeholder-value-x"):
            self.assertFalse(self._hit(f'api_key = "{v}"'), f"占位符被误判：{v}")

    def test_short_value_is_not_a_key(self):
        self.assertFalse(self._hit('token = "abc"'))

    def test_docs_mentioning_sk_prefix(self):
        self.assertFalse(self._hit("密钥形如 sk-xxx，请放进环境变量"))

    def test_scanner_does_not_flag_itself(self):
        """扫描器自己写满了凭证正则，扫自己必然自爆。"""
        self.assertEqual(ss.scan_file(Path(ss.__file__)), [])


class RealRepoTests(unittest.TestCase):
    def test_the_file_that_started_this_is_clean(self):
        """当初被误提交的那个文件：现在应当既不在库里、也扫不出凭证。"""
        p = ROOT / "console" / "_workbench" / "运行数据" / "agent-bridge" / "providers.json"
        if not p.is_file():
            self.skipTest("providers.json 不在本机")
        self.assertEqual(ss.scan_file(p), [])

    def test_hooks_are_installed(self):
        """钩子必须真的装到 .git/hooks —— 存在版本库里不等于生效。"""
        import subprocess

        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "install_hooks.py"), "--check"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(r.returncode, 0, f"钩子未安装：{r.stdout}\n"
                                          f"装一下：python scripts/install_hooks.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
