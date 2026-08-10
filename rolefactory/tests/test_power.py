"""判定力核算自测（纯离线）：最小可判效应、所需题量、逐题分反算 sd。

这套数算出来的「需 25 题」现在被写进了 PERF.md §10 与项目总表的下一刀，
是承重结论，必须有测试守着，不能靠手算一次就信。

跑法：python -m tests.test_power   （在 rolefactory/ 下）
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from power_check import Z95, _derive_sd, analyse  # noqa: E402


def row(**kw):
    base = {"run_id": "r", "role": "测试", "reps": 3, "n": 6, "mean_delta": 1.41,
            "sd_delta": 3.54, "sd_estimated": False, "ci95": None,
            "significant": False, "source": "run"}
    return {**base, **kw}


class MdeTests(unittest.TestCase):
    def test_mde_is_ci_half_width(self):
        out = analyse(row())
        self.assertAlmostEqual(out["mde"], round(Z95 * 3.54 / math.sqrt(6), 2), places=2)
        self.assertAlmostEqual(out["mde"], 2.83, places=2)

    def test_needed_n_matches_formula(self):
        out = analyse(row())
        # n > (1.96·sd/|Δ|)² = (1.96·3.54/1.41)² ≈ 24.2 → 25
        self.assertEqual(out["needed_n"], math.ceil((Z95 * 3.54 / 1.41) ** 2))
        self.assertEqual(out["needed_n"], 25)

    def test_effect_larger_than_noise_needs_nothing_more(self):
        # 产品分析专家那一档：Δ=4.33 sd=4.23 n=5 → 半宽 3.71 < 4.33，已足够
        out = analyse(row(n=5, mean_delta=4.33, sd_delta=4.23, reps=1))
        self.assertEqual(out["needed_n"], 5)
        self.assertIn("已足够", out["verdict"])

    def test_sign_does_not_matter(self):
        # 负分差同样要能算：判定问的是「能不能判」，不是「是不是赢」
        pos = analyse(row(mean_delta=2.0))
        neg = analyse(row(mean_delta=-2.0))
        self.assertEqual(pos["needed_n"], neg["needed_n"])

    def test_missing_sd_is_reported_not_guessed(self):
        out = analyse(row(sd_delta=None))
        self.assertIsNone(out["mde"])
        self.assertIsNone(out["needed_n"])
        self.assertIn("算不了", out["verdict"])

    def test_zero_delta_gives_mde_but_no_needed_n(self):
        # 分差为 0 时「所需题量」无意义（公式会炸），只报最小可判效应
        out = analyse(row(mean_delta=0.0))
        self.assertIsNotNone(out["mde"])
        self.assertIsNone(out["needed_n"])

    def test_single_case_cannot_be_analysed(self):
        out = analyse(row(n=1))
        self.assertIsNone(out["mde"])


class DeriveSdTests(unittest.TestCase):
    def test_derive_from_by_case(self):
        hold = {
            "champion": {"by_case": {"a": 80.0, "b": 90.0, "c": 70.0}},
            "baseline": {"by_case": {"a": 75.0, "b": 80.0, "c": 75.0}},
        }
        mean, sd, n = _derive_sd(hold)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(mean, (5 + 10 - 5) / 3, places=2)
        # 样本标准差（n−1）：deltas = [5, 10, −5]
        deltas = [5.0, 10.0, -5.0]
        m = sum(deltas) / 3
        want = math.sqrt(sum((x - m) ** 2 for x in deltas) / 2)
        self.assertAlmostEqual(sd, round(want, 2), places=2)

    def test_only_paired_cases_count(self):
        # 一臂缺某题就不能配对，必须丢掉而不是当 0 分
        hold = {
            "champion": {"by_case": {"a": 80.0, "b": 90.0, "solo": 50.0}},
            "baseline": {"by_case": {"a": 75.0, "b": 80.0}},
        }
        _, _, n = _derive_sd(hold)
        self.assertEqual(n, 2)

    def test_too_few_cases_returns_none(self):
        hold = {"champion": {"by_case": {"a": 80.0}}, "baseline": {"by_case": {"a": 75.0}}}
        mean, sd, n = _derive_sd(hold)
        self.assertIsNone(sd)
        self.assertEqual(n, 0)

    def test_missing_arms_returns_none(self):
        self.assertEqual(_derive_sd({}), (None, None, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
