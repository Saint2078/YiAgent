"""`must_not_include` 的两侧都要守住。全程离线。

运行：python -m tests.test_must_not（在 rolefactory 目录下）

改这条打分口径的风险是**放过真错答案**，所以「该扣的仍要扣」和
「引用反驳不该扣」两组用例同等重要。用例文本尽量取自实跑回答的真实句式
（见 tools/audit_checks.py 的输出），不是编出来的。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.objective import _hit_must_not_include, score_answer  # noqa: E402

SPEC = {
    "type": "must_not_include",
    "id": "wrong_ship",
    "weight": 15,
    "desc": "不得仅凭 p<0.05 建议全量上线",
    "groups": [{"label": "错误上线断言", "any": ["可以全量上线", "继续全量", "可以上线"]}],
}


class ShouldNotPenalizeTests(unittest.TestCase):
    """引用错误说法并否掉它 —— 这是**答对**的表现，不能扣分。"""

    def test_negated_in_same_sentence(self):
        s, note = _hit_must_not_include("结论先行：**不能继续全量**，应立即暂停推进并回滚", SPEC)
        self.assertEqual(s, 1.0)
        self.assertIn("已否定", note)

    def test_trap_walkthrough(self):
        # 实跑里最常见的一种：复述错误算法以指出陷阱
        text = "1. **分母错用 8h：** 若用 6h/8h=75%，会误判为可以上线"
        self.assertEqual(_hit_must_not_include(text, SPEC)[0], 1.0)

    def test_multiple_occurrences_all_negated(self):
        text = "不能继续全量。第二点：也不应继续全量，除非补齐样本量"
        self.assertEqual(_hit_must_not_include(text, SPEC)[0], 1.0)


class ShouldStillPenalizeTests(unittest.TestCase):
    """真的给出错误断言 —— 必须照旧扣光，否则这条 check 就废了。"""

    def test_bare_assertion(self):
        s, note = _hit_must_not_include("p=0.02 显著，可以全量上线，本周发布", SPEC)
        self.assertEqual(s, 0.0)
        self.assertIn("出现禁止表述", note)

    def test_negation_after_phrase_does_not_excuse(self):
        # 否定线索在禁词**之后**：不认。避免「可以上线，风险不大」这类被放过
        self.assertEqual(_hit_must_not_include("可以上线，风险不能忽视", SPEC)[0], 0.0)

    def test_mixed_one_bare_occurrence_is_enough(self):
        text = "不能继续全量。但综合看，可以上线"
        self.assertEqual(_hit_must_not_include(text, SPEC)[0], 0.0)

    def test_cross_sentence_refutation_not_credited(self):
        # 明确的口径选择：跨句反驳需要理解指代，程序判不可靠，宁可漏放也不误放。
        # 这条用例把该选择钉住 —— 以后若要放宽，得先想清楚怎么防真错答案。
        self.assertEqual(_hit_must_not_include("老板的结论不成立。报表说可以上线", SPEC)[0], 0.0)

    def test_cue_too_far_away(self):
        far = "不能" + "另外还有很多需要考虑的因素" * 5 + "，可以上线"
        self.assertEqual(_hit_must_not_include(far, SPEC)[0], 0.0)


class ScoreAnswerIntegrationTests(unittest.TestCase):
    """走完整打分：改动只影响这一类 check，总分按权重变化。"""

    CHECKS = [
        SPEC,
        {
            "type": "must_include",
            "id": "trap",
            "weight": 25,
            "groups": [{"label": "口径", "any": ["样本量"]}],
        },
    ]

    def test_refuting_answer_keeps_full_weight(self):
        got = score_answer("不能继续全量，样本量不足", self.CHECKS)
        self.assertAlmostEqual(got["total"], 100.0, places=1)

    def test_wrong_answer_loses_that_weight(self):
        got = score_answer("可以上线，样本量够了", self.CHECKS)
        # 只丢禁词那 15 分权重：25/(15+25) = 62.5
        self.assertAlmostEqual(got["total"], 62.5, places=1)


class NumericShareGateTests(unittest.TestCase):
    """出题自校必须挡住「尺子分辨率不足」的题（numeric 权重占比过低）。

    这条门禁的代价是被打回的题要重生成（多花一次调用），所以边界要钉死：
    45% 以下打回，45% 及以上放行。
    """

    def _case(self, numeric_w: float, other_w: float) -> dict:
        return {
            "id": "t01",
            "messages": [{"role": "user", "content": "数据：100、200、300，求增长率"}],
            "checks": [
                {
                    "type": "numeric",
                    "id": "n1",
                    "weight": numeric_w,
                    "target": 100.0,
                    "computation": "(200-100)/100*100",
                },
                {
                    "type": "must_include",
                    "id": "m1",
                    "weight": other_w,
                    "groups": [{"label": "口径", "any": ["口径"]}],
                },
                SPEC,
            ],
        }

    def test_low_numeric_share_rejected(self):
        from app.objective import verify_case  # noqa: PLC0415

        ok, problems = verify_case(self._case(30, 55))  # 30/100 = 30%
        self.assertFalse(ok)
        self.assertTrue(any("分辨率" in p for p in problems), problems)

    def test_sufficient_numeric_share_passes(self):
        from app.objective import verify_case  # noqa: PLC0415

        ok, problems = verify_case(self._case(60, 25))  # 60/100 = 60%
        self.assertTrue(ok, problems)

    def test_boundary_45_percent_passes(self):
        from app.objective import verify_case  # noqa: PLC0415

        ok, problems = verify_case(self._case(45, 40))
        self.assertTrue(ok, problems)


if __name__ == "__main__":
    unittest.main(verbosity=2)
