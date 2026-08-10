"""train / holdout 切分自测。全程离线。运行：python -m tests.test_split（在 rolefactory 目录下）。

这里守一条容易被忽略的事实：**holdout 题量不由出题量决定**。
`per_dim`（每维出几道）从 2 提到 10，train 会从 6 涨到 54，而 holdout 仍是每维 1 道。
判定泛化的瓶颈恰恰是 holdout 题量（PERF.md §10.1），所以每维留几道必须能单独调。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.roles import split_holdout  # noqa: E402


def cases(dims: int, per_dim: int) -> list[dict]:
    return [
        {"id": f"d{d}_case_{i:02d}", "dimension_key": f"dim_{d}"}
        for d in range(dims)
        for i in range(per_dim)
    ]


class SplitTests(unittest.TestCase):
    def test_default_locks_holdout_to_dimension_count(self):
        # 这条不是「期望行为」，是**必须被记住的限制**：出题翻五倍，holdout 一道没多。
        for per_dim in (2, 5, 10):
            train, hold = split_holdout(cases(6, per_dim))
            self.assertEqual(len(hold), 6, f"per_dim={per_dim}")
            self.assertEqual(len(train), 6 * per_dim - 6)

    def test_holdout_per_dim_scales_holdout(self):
        train, hold = split_holdout(cases(6, 10), per_dim=9)
        self.assertEqual(len(hold), 54)  # 6 维 × 9 道 —— 够到 §10.1 要的量级
        self.assertEqual(len(train), 6)

    def test_never_starves_train(self):
        # 每维至少留 1 道给 train：train 空了进化就没有可优化的目标。
        train, hold = split_holdout(cases(4, 3), per_dim=99)
        self.assertEqual(len(train), 4)
        self.assertEqual(len(hold), 8)

    def test_single_case_dimension_goes_to_train(self):
        mixed = cases(1, 1) + [{"id": "d9_case_00", "dimension_key": "dim_9"}]
        train, hold = split_holdout(mixed, per_dim=3)
        self.assertEqual(hold, [])
        self.assertEqual(len(train), 2)

    def test_no_leakage_and_no_loss(self):
        all_cases = cases(5, 4)
        train, hold = split_holdout(all_cases, per_dim=2)
        t_ids, h_ids = {c["id"] for c in train}, {c["id"] for c in hold}
        self.assertEqual(t_ids & h_ids, set(), "同一题不能既训练又鉴定")
        self.assertEqual(t_ids | h_ids, {c["id"] for c in all_cases}, "不能丢题")

    def test_stratified_across_dimensions(self):
        # holdout 必须覆盖每个维度，否则「未见题」只测了部分能力面。
        _, hold = split_holdout(cases(6, 4), per_dim=2)
        self.assertEqual(len({c["dimension_key"] for c in hold}), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
