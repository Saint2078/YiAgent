"""筛题门槛 `roles.drop_saturated` 的护栏测试（离线，不发任何调用）。

这道门槛会**删题**，所以护栏比功能更重要：删多了会把维度删空、把题组删干，
而这两件事都不会报错，只会让后面的结论建立在残缺题组上。

用法：python -m tests.test_headroom_gate
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import roles  # noqa: E402


def case(cid: str, dim: str = "d1") -> dict:
    return {"id": cid, "dimension_key": dim, "dimension": dim}


class DropSaturatedTests(unittest.TestCase):
    def test_drops_only_above_ceiling(self):
        cs = [case("a"), case("b"), case("c"), case("d")]
        scores = {"a": 100.0, "b": 60.0, "c": 70.0, "d": 80.0}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0)
        self.assertEqual([c["id"] for c in dropped], ["a"])
        self.assertEqual([c["id"] for c in keep], ["b", "c", "d"])

    def test_never_drops_more_than_half_a_dimension(self):
        # 一整维全是满分题：不许清空，只准扔一半（且扔最容易的）
        cs = [case(x) for x in "abcd"]
        scores = {"a": 100.0, "b": 99.0, "c": 98.0, "d": 97.0}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0)
        self.assertEqual(len(dropped), 2, "扔超过了一半")
        self.assertEqual(len(keep), 2)
        # 留下的必须是**较难**的那两道（分数低的）
        self.assertEqual(sorted(c["id"] for c in keep), ["c", "d"])

    def test_two_case_dimension_keeps_one(self):
        cs = [case("a"), case("b")]
        keep, dropped = roles.drop_saturated(cs, {"a": 100.0, "b": 100.0}, ceiling=90.0)
        self.assertEqual(len(keep), 1)
        self.assertEqual(len(dropped), 1)

    def test_single_case_dimension_never_emptied(self):
        # 2 题 × 0.5 = 1 可扔；1 题 × 0.5 向下取整 = 0 可扔 → 单题维度必然留下
        keep, dropped = roles.drop_saturated([case("a")], {"a": 100.0}, ceiling=90.0)
        self.assertEqual([c["id"] for c in keep], ["a"])
        self.assertEqual(dropped, [])

    def test_stratification_preserved_across_dimensions(self):
        cs = [case("a1", "d1"), case("a2", "d1"), case("b1", "d2"), case("b2", "d2")]
        scores = {"a1": 100.0, "a2": 100.0, "b1": 50.0, "b2": 55.0}
        keep, _ = roles.drop_saturated(cs, scores, ceiling=90.0)
        dims = {c["dimension_key"] for c in keep}
        self.assertEqual(dims, {"d1", "d2"}, "有维度被整个扔空")

    def test_missing_score_is_treated_as_hardest(self):
        # 探针失败的题按最难处理：宁可留下钝题，也不能因为"没探到分"而误杀
        cs = [case("a"), case("b")]
        keep, dropped = roles.drop_saturated(cs, {"b": 100.0}, ceiling=90.0)
        self.assertEqual([c["id"] for c in keep], ["a"])
        self.assertEqual([c["id"] for c in dropped], ["b"])

    def test_ceiling_100_disables_gate(self):
        cs = [case("a"), case("b")]
        keep, dropped = roles.drop_saturated(cs, {"a": 100.0, "b": 100.0}, ceiling=100.0)
        self.assertEqual(len(keep), 2)
        self.assertEqual(dropped, [])

    def test_no_case_is_lost_or_duplicated(self):
        cs = [case(f"c{i}", f"d{i % 3}") for i in range(12)]
        scores = {f"c{i}": float(50 + i * 5) for i in range(12)}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0)
        ids = [c["id"] for c in keep] + [c["id"] for c in dropped]
        self.assertEqual(sorted(ids), sorted(c["id"] for c in cs))
        self.assertEqual(len(set(ids)), len(cs), "有题被重复计入")


class ReserveTests(unittest.TestCase):
    """余量护栏：筛题**不许把 holdout 削小**。

    这条是空跑在真实题组上抓出来的：没有它时，`split_holdout` 每维只从尾部取
    `per_dim` 道且必须给 train 留 1 道，于是某维只剩 1 道就贡献 0 道 holdout ——
    实测 Product 的 holdout 从 5 道掉到 1 道。拿天花板问题换样本量问题，净亏。
    """

    def _suite(self, per_dim: int, dims: int = 3) -> list[dict]:
        return [case(f"d{d}c{i}", f"d{d}") for d in range(dims) for i in range(per_dim)]

    def test_no_op_when_no_slack(self):
        # 每维 2 道、holdout_per_dim=1 → 需保留 2 道 → 没有余量，必须什么都不扔
        cs = self._suite(per_dim=2)
        scores = {c["id"]: 100.0 for c in cs}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0, reserve_per_dim=2)
        self.assertEqual(dropped, [], "没有余量时仍然扔了题")
        self.assertEqual(len(keep), len(cs))

    def test_drops_only_the_slack(self):
        # 每维 8 道、需保留 5 道 → 余量 3；半数上限 4 → 取小 = 3
        cs = self._suite(per_dim=8)
        scores = {c["id"]: 100.0 for c in cs}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0, reserve_per_dim=5)
        self.assertEqual(len(dropped), 3 * 3, "每维应恰好扔 3 道")
        for d in range(3):
            left = [c for c in keep if c["dimension_key"] == f"d{d}"]
            self.assertEqual(len(left), 5)

    def test_holdout_never_shrinks(self):
        """真正要守的不变量：筛完之后 holdout 题量不许下降。"""
        for per_dim in (2, 4, 6, 8, 12):
            for hpd in (1, 2, 4):
                cs = self._suite(per_dim=per_dim)
                # 一半的题贴天花板，另一半正常
                scores = {c["id"]: (100.0 if i % 2 else 60.0) for i, c in enumerate(cs)}
                _, hold_before = roles.split_holdout(cs, per_dim=hpd)
                keep, _ = roles.drop_saturated(
                    cs, scores, ceiling=90.0, reserve_per_dim=1 + hpd
                )
                _, hold_after = roles.split_holdout(keep, per_dim=hpd)
                self.assertGreaterEqual(
                    len(hold_after), len(hold_before),
                    f"per_dim={per_dim} holdout_per_dim={hpd}："
                    f"holdout 从 {len(hold_before)} 掉到 {len(hold_after)}",
                )


class ProbeIndependenceTests(unittest.TestCase):
    """探针必须是**独立采样**，否则筛题与算分共用一次测量 → Δ 被选择偏差抬高。"""

    def test_probe_rep_differs_from_scoring_reps(self):
        from app import pipeline

        self.assertLess(pipeline.PROBE_REP, 0,
                        "探针 rep 必须落在评分用的 0..n 之外")

    def test_probe_salt_differs_from_scoring_salt(self):
        # 缓存键是 sig|case|rep{rep}；探针与 rep0 必须产生不同的键
        from app import pipeline

        probe = f"baseline|case1|rep{pipeline.PROBE_REP}"
        for r in range(8):
            self.assertNotEqual(probe, f"baseline|case1|rep{r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
