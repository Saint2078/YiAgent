"""试跑中断时，**已经落盘的门槛验证不该跟着异常一起丢掉**。

由来（真事）：PM 门槛试跑在 baseline 35/72 处额度耗尽，`wait_run` 抛异常，
`gate_pilot` 直接 `return 1`，日志只剩一行「试跑失败」。
但这次试跑要验的**恰恰是门槛与切分**，它们在 probe/bank 相位就已完成并落盘：
扔了 29 道、holdout 91 道、train 封在 6 道 —— 四条检查全部可判，
却因为**后面一步**失败而被丢弃。再验一遍要十几分钟额度，而答案早就在盘上。

这里钉两条：
1. 盘上有切分结果时，中断也要把四条检查跑完；
2. 但「检查过了」不等于「试跑成功」—— 必须分别说清已验哪些、未验哪些，
   否则四条 ok 会被读成整条流水线验通了。

用法：python -m tests.test_pilot_salvage
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import queue_decisive as qd  # noqa: E402

# 真实那次中断留下的形状（97 题 / 扔 29 / train 6 / holdout 91）
REAL_ABORTED_RUN = "20260811-021053-22f4c1"


class LoadReportTests(unittest.TestCase):
    def test_reads_the_real_aborted_run(self):
        rep = qd.load_report(REAL_ABORTED_RUN)
        if not rep:
            self.skipTest("这台机器上没有那次中断的 run")
        su = rep.get("suite") or {}
        self.assertEqual(len(su.get("holdout") or []), 91)
        self.assertEqual(len(su.get("train") or []), 6)
        self.assertEqual(len(su.get("dropped_saturated") or []), 29)

    def test_missing_run_returns_empty_not_raises(self):
        self.assertEqual(qd.load_report("no-such-run-id"), {})

    def test_corrupt_report_returns_empty(self):
        d = ROOT / "data" / "runs" / "test-corrupt-report"
        d.mkdir(parents=True, exist_ok=True)
        try:
            (d / "report.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(qd.load_report("test-corrupt-report"), {})
        finally:
            (d / "report.json").unlink(missing_ok=True)
            d.rmdir()


class SalvageTests(unittest.TestCase):
    """把那次真实中断重放一遍，确认四条检查真的被跑出来。"""

    def _run_pilot_with_abort(self, run_id: str):
        """重放一次「起 run → 后段崩掉」，**不许**把桩写错就悄悄跳过。

        第一版这两条测试因为桩对不上而 skip 了，我差点当它们通过 ——
        而 skip 掉的恰恰是"抢救逻辑到底管不管用"这个唯一要问的问题。
        所以这里把依赖照实列全（TEAM / RUN_PARAMS / 额度探针），桩错就让它红。
        """
        lines: list[str] = []

        class FakeBD:
            TEAM = [{"seat": "PM", "factory_role": "项目经理"}]
            RUN_PARAMS = {"per_dim": 21, "train_per_dim": 1, "headroom_ceiling": 90,
                          "variants_per_gen": 10, "generations": 3}

            @staticmethod
            def start_run(_role):
                return run_id

            @staticmethod
            def wait_run(_rid):
                raise RuntimeError(
                    f"run_failed:{run_id}:aborted:answer HTTP 403: usage limit")

        class FakeProbe:
            returncode = 0
            stdout = "QUOTA OK"
            stderr = ""

        with patch.object(qd, "log", side_effect=lambda m: lines.append(str(m))), \
                patch.dict(sys.modules, {"build_devteam": FakeBD}), \
                patch.object(qd.subprocess, "run", return_value=FakeProbe()), \
                patch.object(qd.heartbeat, "beat"), \
                patch.object(qd.heartbeat, "keep_beating",
                             side_effect=lambda *a, **k: _NullCtx()):
            rc = qd.gate_pilot("PM", probe_every=1)
        return rc, "\n".join(lines)

    def test_checks_still_run_after_abort(self):
        if not qd.load_report(REAL_ABORTED_RUN):
            self.skipTest("这台机器上没有那次中断的 run")
        _rc, text = self._run_pilot_with_abort(REAL_ABORTED_RUN)
        self.assertIn("门槛真的扔题了", text, "中断后四条检查没有被跑出来")
        self.assertIn("holdout ≥ 题量下限", text)

    def test_salvaged_checks_report_the_real_numbers(self):
        """抢救出来的数必须是那次真实的 97/29/6/91，不能是默认值或空壳。"""
        if not qd.load_report(REAL_ABORTED_RUN):
            self.skipTest("这台机器上没有那次中断的 run")
        _rc, text = self._run_pilot_with_abort(REAL_ABORTED_RUN)
        for token in ("97", "29", "91"):
            self.assertIn(token, text, f"抢救出的报告里没有 {token}")

    def test_partial_run_is_not_reported_as_full_success(self):
        """四条 ok **不能**读成整条流水线验通了。"""
        if not qd.load_report(REAL_ABORTED_RUN):
            self.skipTest("这台机器上没有那次中断的 run")
        _rc, text = self._run_pilot_with_abort(REAL_ABORTED_RUN)
        self.assertIn("中断", text, "没说这次 run 是中断的")
        self.assertIn("未验", text, "没说清哪些相位没验到")

    def test_abort_with_nothing_on_disk_still_fails(self):
        """盘上没切分结果时必须照旧失败 —— 抢救不能变成"总是报成功"。"""
        rc, text = self._run_pilot_with_abort("no-such-run-id")
        self.assertEqual(rc, 1, "什么都没验到却没返回失败")
        self.assertIn("什么都没验到", text)


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class GateOutcomeTests(unittest.TestCase):
    """门槛在真实数据上的行为：两条机制**都**要能解释清楚。

    实测 126 道里 41 道 ≥90，只扔了 29 道。差额不是 bug，是两件事叠加：
      · 门槛是**严格大于**（>90），恰好等于 90.0 的 3 道留下；
      · `reserve_per_dim` 保底，resource_feasibility_check 一维 19 道饱和，
        被强制留下 9 道以保住该维覆盖。
    我第一次判读时把全部差额归给 reserve，是错的 —— 所以这条按数字钉住。
    """

    def test_threshold_is_strictly_greater(self):
        d = ROOT / "data" / "runs" / REAL_ABORTED_RUN
        if not (d / "probe.json").is_file():
            self.skipTest("没有那次 probe 明细")
        sc = json.loads((d / "probe.json").read_text(encoding="utf-8"))["scores"]
        st = json.loads((d / "state.json").read_text(encoding="utf-8"))
        dropped = {x["id"] for x in (st.get("dropped_saturated") or [])}
        at_ceiling = [c for c, v in sc.items() if v == 90.0]
        self.assertTrue(at_ceiling, "这批数据里没有恰好 90 分的题，钉不住这条")
        for c in at_ceiling:
            self.assertNotIn(c, dropped, "恰好等于门槛的题被扔了 —— 门槛不是严格大于")

    def test_every_dropped_case_is_above_ceiling(self):
        d = ROOT / "data" / "runs" / REAL_ABORTED_RUN
        if not (d / "probe.json").is_file():
            self.skipTest("没有那次 probe 明细")
        sc = json.loads((d / "probe.json").read_text(encoding="utf-8"))["scores"]
        st = json.loads((d / "state.json").read_text(encoding="utf-8"))
        ceiling = float((st.get("params") or {}).get("headroom_ceiling") or 90)
        for x in (st.get("dropped_saturated") or []):
            self.assertGreater(
                float(x["baseline"]), ceiling,
                f"扔了一道没到门槛的题：{x['id']} = {x['baseline']}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
