"""reps 的「要多少 / 给多少」必须对得上账。

由来：队列按决策发 `reps=15`，服务端 `min(8, ...)` **静默**截成 8。
客户端日志写「复核开始 reps=15」→「复核完成」，全程没有一处提示，
盘上却是每格 8 次（96 行明细而不是 180）。下游方差分解拿 8 当输入算得毫无破绽 ——
只有回头逐条点明细才发现。

这类错最贵的地方不是数字小了一半，而是**它带着一个"成功"的回复**：
决策依据（reps=15 能把半宽压到 1.3）与实际执行（reps=8）不同源，
而两边都没报错。所以这里钉三条：

1. 服务端可以截断（成本护栏，合理），但**必须在回复里说**；
2. 客户端拿到不同的值必须喊出来；
3. 队列排计划时按真实上限估评测数，别在日志里写一个假数。

用法：python -m tests.test_reps_contract
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


class ServerClampTests(unittest.TestCase):
    """服务端截断的**行为**：截了要说，没截别加噪声。"""

    def _clamp(self, requested: int) -> tuple[int, bool]:
        """复刻 main.py 里的截断口径。

        这里刻意复刻而不是 import：`post_reholdout` 是个 async 端点，
        真调它要连服务和额度。截断本身是纯算术，复刻它能在 0 额度下钉住边界，
        而"复刻会不会和真实实现漂移"由下面 test_endpoint_source_matches 兜住。
        """
        cap = 8
        eff = max(1, min(cap, requested))
        return eff, eff != requested

    def test_over_cap_is_clamped(self):
        eff, clamped = self._clamp(15)
        self.assertEqual(eff, 8)
        self.assertTrue(clamped, "截断了却没标记 —— 这正是当初没被发现的原因")

    def test_within_cap_is_untouched(self):
        for r in (1, 3, 8):
            eff, clamped = self._clamp(r)
            self.assertEqual(eff, r)
            self.assertFalse(clamped, f"reps={r} 没被截断，不该报截断")

    def test_zero_and_negative_are_floored_to_one(self):
        for r in (0, -5):
            eff, _ = self._clamp(r)
            self.assertEqual(eff, 1, "reps 必须至少 1，否则会跑出 0 次评测的空复核")

    def test_endpoint_source_matches_the_replicated_cap(self):
        """上面复刻的上限必须和真实端点一致 —— 否则这组测试在保护一个幻觉。

        只断言"上限这个数字"，不断言措辞：数字漂移会让复刻失效，措辞变不会。
        """
        src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        m = re.search(r"min\(\s*(\d+)\s*,\s*reps_requested\s*\)", src)
        self.assertIsNotNone(m, "找不到 reholdout 的 reps 截断表达式（实现可能改了写法）")
        self.assertEqual(int(m.group(1)), 8, "服务端上限变了，请同步本测试与 queue 的估算")

    def test_endpoint_surfaces_the_clamp(self):
        """截断必须写进回复 —— 这是当初唯一缺的那一环。"""
        src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        for key in ("reps_requested", "reps_clamped"):
            self.assertIn(key, src, f"回复里没有 {key}，调用方无法对账")


class QueuePlanTests(unittest.TestCase):
    def test_plan_reps_does_not_exceed_server_cap(self):
        """队列不该排一个服务端注定要截掉的 reps —— 那会让日志里的评测数是假的。"""
        import queue_decisive as qd

        for seat, reps, _evals in qd.PLAN:
            self.assertLessEqual(
                reps, qd.SERVER_REPS_CAP,
                f"{seat} 排了 reps={reps}，服务端上限 {qd.SERVER_REPS_CAP}，会被静默截断",
            )

    def test_plan_eval_estimate_matches_reps(self):
        """预计评测数必须由 reps 推出来，不能是手写的常数（手写就是它当初为什么会假）。

        口径：题数 × 2 臂 × reps。
        """
        import queue_decisive as qd

        for seat, reps, evals in qd.PLAN:
            self.assertEqual(
                evals % (2 * reps), 0,
                f"{seat} 的评测数 {evals} 不是 2×reps({reps}) 的整数倍，估算口径对不上",
            )
            cases = evals // (2 * reps)
            self.assertGreater(cases, 0, f"{seat} 推不出正的题数")
            self.assertLess(cases, 200, f"{seat} 推出的题数 {cases} 不合理")


class ClientReconcileTests(unittest.TestCase):
    def test_client_compares_requested_against_returned(self):
        """客户端必须拿回复里的 reps 和请求值对账。

        断言"它读了 body 里的 reps 并与 args.reps 比较"这个行为的痕迹，
        而不是断言告警文案 —— 文案会改，对账不该消失。
        """
        src = (ROOT / "tools" / "run_reholdout.py").read_text(encoding="utf-8")
        self.assertIn('body.get("reps")', src, "客户端没读服务端实际用的 reps")
        self.assertRegex(src, r"got_reps\s*!=\s*args\.reps", "客户端没做请求/实际对账")

    def test_client_logs_actual_reps_in_result_line(self):
        """结果行里要带实际 reps —— 否则日志留下的仍是那个请求值。"""
        src = (ROOT / "tools" / "run_reholdout.py").read_text(encoding="utf-8")
        self.assertRegex(src, r"复核完成.*reps=\{got_reps\}", "结果行没打实际 reps")


if __name__ == "__main__":
    unittest.main(verbosity=2)
