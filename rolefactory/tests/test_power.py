"""判定力核算自测（纯离线）：最小可判效应、所需题量、逐题分反算 sd。

这套数算出来的「需 25 题」现在被写进了 PERF.md §10 与项目总表的下一刀，
是承重结论，必须有测试守着，不能靠手算一次就信。

跑法：python -m tests.test_power   （在 rolefactory/ 下）
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from power_check import Z95, _derive_sd, analyse  # noqa: E402
from variance_decomp import decompose, half_width, load_cells  # noqa: E402


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


class VarianceDecompTests(unittest.TestCase):
    """方差分解：把「该加重复还是加题」的处方守住。

    这套数给出的结论（6 题无论重复多少次都判不了、最省配法是 reps=1 × 55 题）
    写进了 PERF.md §10.1 与项目总表的下一刀，必须有测试。
    """

    def cells(self, *, within_spread: float, between_spread: float, reps: int = 3):
        """造一批 (臂, 题) → 逐次分数：题间差异与题内噪声可分别调。"""
        out: dict[tuple[str, str], list[float]] = {}
        for ci in range(6):
            base_level = 80.0 + ci * between_spread
            for arm in ("baseline", "champ"):
                bump = 2.0 if arm == "champ" else 0.0
                # 用 ±spread 交替造出确定的题内方差，避免测试依赖随机数
                out[(arm, f"case_{ci}")] = [
                    base_level + bump + (within_spread if i % 2 == 0 else -within_spread)
                    for i in range(reps)
                ]
        return out

    def test_pure_within_noise_gives_zero_between(self):
        # 所有题同一水平 → 题间差异应被判为 0（原始估计可能为负，按 0 处理）
        d = decompose(self.cells(within_spread=5.0, between_spread=0.0), "champ", "baseline")
        self.assertEqual(d["var_between"], 0.0)
        self.assertGreater(d["var_within"], 0)

    def test_pure_between_variation_gives_zero_within(self):
        # 每次重复完全一致 → 题内噪声为 0，分差方差全归题间
        d = decompose(self.cells(within_spread=0.0, between_spread=4.0), "champ", "baseline")
        self.assertEqual(d["var_within"], 0.0)

    def test_half_width_shrinks_with_reps_but_has_floor(self):
        # 关键性质：reps→∞ 时半宽收敛到 1.96·σ_b/√n，压不到 0
        var_b, var_w, n = 4.62, 11.83, 6  # PM 实测量级
        wide = half_width(var_b, var_w, n, 1)
        narrow = half_width(var_b, var_w, n, 30)
        floor = Z95 * math.sqrt(var_b) / math.sqrt(n)
        self.assertGreater(wide, narrow)
        self.assertGreater(narrow, floor)
        self.assertAlmostEqual(half_width(var_b, 0.0, n, 1), floor, places=6)

    def test_more_cases_is_cheaper_than_more_reps(self):
        # 达到同一半宽：题数线性压、重复只压 1/r，所以 reps 小题多总评测数更省。
        # 这条是 PERF.md §10.1 的处方，别被「加重复更省事」的直觉改掉。
        var_b, var_w, delta = 4.62, 11.83, 1.41
        cost = {}
        for r in (1, 3, 10):
            n = math.ceil((Z95 / delta) ** 2 * (var_b + 2 * var_w / r))
            cost[r] = 2 * n * r
        self.assertLess(cost[1], cost[3])
        self.assertLess(cost[3], cost[10])


class HoldoutSelectionTests(unittest.TestCase):
    """holdout 题号必须取报告里那份名单，不许按题号后缀猜。

    猜法曾经能对上：早期每维只留一道 `medium_02` 当 holdout。`holdout_per_dim` 一开大
    就错了，而且**错得不报错** —— 捞到 6 道 train 题，照样算出个像真的 Δ（PERF.md §16）。
    """

    def setUp(self):
        import tempfile
        import variance_decomp as vd

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        run = Path(self.tmp.name) / "rid"
        run.mkdir()
        # holdout 是 h0..h2，train 是 t_medium_02 —— 后缀恰好长得像旧口径的 holdout
        hold = ["h0", "h1", "h2"]
        (run / "report.json").write_text(
            json.dumps({"scores": {"holdout": {"cases": hold}}}), encoding="utf-8"
        )
        rows = []
        for case, score in [("h0", 80.0), ("h1", 82.0), ("h2", 84.0), ("t_medium_02", 10.0)]:
            for arm in ("baseline", "champ"):
                rows.append({"case": case, "variant": arm, "rep": 0,
                             "score": score + (2.0 if arm == "champ" else 0.0)})
        (run / "results.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows), encoding="utf-8"
        )
        self._orig_runs = vd.RUNS
        vd.RUNS = Path(self.tmp.name)
        self.addCleanup(lambda: setattr(vd, "RUNS", self._orig_runs))

    def test_uses_report_case_list_not_suffix(self):
        cells, champ, base, origin = load_cells("rid", "medium_02")
        self.assertEqual(origin, "report.json")
        self.assertEqual(champ, "champ")
        self.assertEqual({c for _, c in cells}, {"h0", "h1", "h2"})
        # 那道 train 题必须被排除，否则 −70 分的离群值会把 sd 撑爆
        self.assertNotIn(("champ", "t_medium_02"), cells)

    def test_falls_back_to_suffix_when_report_has_no_list(self):
        import variance_decomp as vd

        (vd.RUNS / "rid" / "report.json").write_text(
            json.dumps({"scores": {"holdout": {}}}), encoding="utf-8"
        )
        cells, _, _, origin = load_cells("rid", "medium_02")
        self.assertIn("后缀", origin)  # 退路必须自报身份，别让人以为读的是名单
        self.assertEqual({c for _, c in cells}, {"t_medium_02"})


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
