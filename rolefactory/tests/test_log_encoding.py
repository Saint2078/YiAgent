"""日志**不许**因为编码而抛异常。

由来（真崩过）：抢救逻辑里那行告警带了个 `⚠`，在 stdout 编码为 GBK 的环境下
抛 `UnicodeEncodeError` —— 而且崩在**四条检查都跑完之后**：
「这次 run 是中断的、哪些相位没验到」那段话没打出来，进程带异常退出，
看起来像抢救逻辑自己失败了。仪表把任务弄死了。

同一类字符散落在好几处（`⚠` `✓` `✗` `←`），所以不能靠"以后别用了"来防，
得让 `log` 本身在任何编码下都安全。

用法：python -m tests.test_log_encoding
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import queue_decisive as qd  # noqa: E402
import run_reholdout as rr  # noqa: E402

# 真实用过的、GBK 编不出来的字符
RISKY = "⚠ ✓ ✗ ← □ ≈"


class GbkStdoutTests(unittest.TestCase):
    """把 stdout 换成 GBK，再打这些字符 —— 必须不抛。"""

    def setUp(self):
        self._real = sys.stdout

    def tearDown(self):
        sys.stdout = self._real

    def _gbk_stdout(self) -> io.TextIOWrapper:
        return io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")

    def test_queue_log_survives_gbk(self):
        sys.stdout = self._gbk_stdout()
        try:
            qd.log(f"中断告警 {RISKY} 说明")
        except UnicodeEncodeError as exc:
            self.fail(f"queue_decisive.log 在 GBK 下抛了：{exc}")

    def test_reholdout_log_survives_gbk(self):
        sys.stdout = self._gbk_stdout()
        try:
            rr.log(f"reps 对账 {RISKY} 说明")
        except UnicodeEncodeError as exc:
            self.fail(f"run_reholdout.log 在 GBK 下抛了：{exc}")

    def test_ascii_only_stdout_also_survives(self):
        """最恶劣的情况：连中文都编不出来（纯 ASCII 流）。"""
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
        try:
            qd.log("全中文告警：门槛试跑中断 ⚠")
            rr.log("全中文告警：复核完成 ✓")
        except UnicodeEncodeError as exc:
            self.fail(f"ASCII 流下抛了：{exc}")

    def test_content_still_readable_when_encodable(self):
        """兜底不能把能显示的内容也一起吃掉 —— 否则等于永久降级成 ASCII。"""
        buf = io.BytesIO()
        sys.stdout = io.TextIOWrapper(buf, encoding="utf-8", errors="strict")
        qd.log("门槛真的扔题了")
        sys.stdout.flush()
        self.assertIn("门槛真的扔题了", buf.getvalue().decode("utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
