"""numeric 权重重加权与保本题量区间的测试。

第一条是校准：一个离线重加权工具**必须先在"原权重"处等于原值**，
再谈它对别的权重的预测。不做这一步就是拿没校准的尺子量取舍。

用法：python -m tests.test_numeric_share
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import need_n_ci  # noqa: E402
import numeric_share_sweep as nss  # noqa: E402


class ReweightCalibrationTests(unittest.TestCase):
    def test_reproduces_original_score_at_natural_share(self):
        """在每行自己的 numeric 份额处，重加权公式必须复现该行原本的分数。"""
        checked = 0
        for _seat, rid in nss.SEATS:
            rows, _ = nss.load(rid)
            for r in rows[:200]:
                checks = r.get("checks") or []
                allw = sum(float(c.get("weight") or 0) for c in checks)
                want = r.get("score")
                if allw <= 0 or not isinstance(want, (int, float)):
                    continue
                nw = sum(float(c.get("weight") or 0) for c in checks
                         if str(c.get("type")) == "numeric")
                got = nss.score_at(r, nw / allw)
                if got is None:
                    continue
                checked += 1
                self.assertAlmostEqual(
                    got, float(want), delta=0.51,
                    msg=f"{rid} {r.get('case')} 复现 {got:.2f} ≠ 原值 {want:.2f}",
                )
        self.assertGreater(checked, 100, "校准样本太少，这条测试没起到作用")

    def test_score_is_linear_in_share(self):
        """总分对份额必须是线性的 —— 中点等于两端平均，否则公式写错了。"""
        row = {"checks": [
            {"type": "numeric", "weight": 40.0, "score": 1.0},
            {"type": "must_include", "weight": 60.0, "score": 0.5},
        ]}
        a, b = nss.score_at(row, 0.2), nss.score_at(row, 0.8)
        mid = nss.score_at(row, 0.5)
        self.assertAlmostEqual(mid, (a + b) / 2, places=6)

    def test_all_numeric_weight_gives_numeric_score(self):
        row = {"checks": [
            {"type": "numeric", "weight": 10.0, "score": 1.0},
            {"type": "must_include", "weight": 90.0, "score": 0.0},
        ]}
        self.assertAlmostEqual(nss.score_at(row, 1.0), 100.0, places=6)
        self.assertAlmostEqual(nss.score_at(row, 0.0), 0.0, places=6)

    def test_missing_numeric_falls_back_without_crashing(self):
        row = {"checks": [{"type": "must_include", "weight": 50.0, "score": 0.4}]}
        self.assertAlmostEqual(nss.score_at(row, 0.6), 40.0, places=6)

    def test_no_checks_returns_none(self):
        self.assertIsNone(nss.score_at({"checks": []}, 0.6))


class NeedNTests(unittest.TestCase):
    def test_zero_delta_needs_infinite_cases(self):
        """Δ=0 时所需题量无上界 —— 不能返回一个具体数字骗人。"""
        self.assertEqual(need_n_ci.need_n([1.0, -1.0]), float("inf"))

    def test_need_n_scales_with_sd_squared(self):
        """n ∝ sd²：这正是它对小样本极度敏感的原因，钉住这条依赖关系。"""
        small = need_n_ci.need_n([9.0, 10.0, 11.0])
        big = need_n_ci.need_n([8.0, 10.0, 12.0])
        self.assertAlmostEqual(big / small, 4.0, delta=0.01)

    def test_single_case_is_undefined(self):
        self.assertEqual(need_n_ci.need_n([5.0]), float("inf"))

    def test_identical_deltas_need_no_cases(self):
        n = need_n_ci.need_n([5.0, 5.0, 5.0])
        self.assertTrue(math.isfinite(n))
        self.assertLess(n, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
