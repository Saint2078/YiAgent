"""放宽字面匹配的重打分工具测试。

这个工具得出的是**否证**结论（放宽字面匹配救不了判定力），
所以它自己必须先站得住 —— 否则"证伪"只是工具写错了。

用法：python -m tests.test_lexical_slack
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import lexical_slack as ls  # noqa: E402


class BigramTests(unittest.TestCase):
    def test_bigrams_of_chinese(self):
        self.assertEqual(ls.bigrams("分母口径"), ["分母", "母口", "口径"])

    def test_bigrams_ignore_whitespace(self):
        self.assertEqual(ls.bigrams("分 母"), ["分母"])

    def test_single_char_degrades_gracefully(self):
        self.assertEqual(ls.bigrams("分"), ["分"])

    def test_empty_string(self):
        self.assertEqual(ls.bigrams(""), [])


class RelaxedHitTests(unittest.TestCase):
    def test_exact_substring_still_hits(self):
        self.assertTrue(ls.relaxed_hit("分母包含未完成引导的用户", ["分母包含未完成"], 0.8))

    def test_paraphrase_hits_when_relaxed(self):
        """这正是当初的动机：语义对、措辞不同，现行口径判 0。"""
        answer = "分母是全部自然新注册用户，含未完成引导与流失用户"
        syn = "全部新注册用户作为分母"
        self.assertFalse(syn in answer, "前提变了：这条不再是「换措辞」的例子")
        self.assertTrue(ls.relaxed_hit(answer, [syn], 0.5))

    def test_unrelated_text_does_not_hit(self):
        self.assertFalse(ls.relaxed_hit("今天天气不错，我们去散步吧", ["全部新注册用户作为分母"], 0.8))

    def test_threshold_is_monotone(self):
        """阈值越高越难命中 —— 这条方向性必须成立，否则扫阈值毫无意义。"""
        answer = "分母是全部自然新注册用户"
        syn = "全部新注册用户作为分母"
        hits = [ls.relaxed_hit(answer, [syn], t) for t in (0.3, 0.6, 0.9, 1.0)]
        # 一旦变 False，后面不能又变回 True
        seen_false = False
        for h in hits:
            if not h:
                seen_false = True
            elif seen_false:
                self.fail(f"阈值不单调：{hits}")

    def test_relaxation_is_never_stricter_than_exact(self):
        """放宽口径必须**包含**精确口径的所有命中，否则它不是「放宽」。"""
        answer = "包含未完成引导的用户都算进分母"
        syns = ["分母", "未完成引导"]
        for t in (0.5, 0.8, 1.0):
            for s in syns:
                if s in answer:
                    self.assertTrue(ls.relaxed_hit(answer, [s], t),
                                    f"精确命中却在放宽口径下未命中（阈值 {t}，词 {s}）")


class ScoreCheckTests(unittest.TestCase):
    def _spec(self) -> dict:
        return {"type": "must_include", "groups": [
            {"label": "A", "any": ["全部新注册用户作为分母"]},
            {"label": "B", "any": ["按 user_id 去重"]},
        ]}

    def test_exact_mode_scores_by_group_coverage(self):
        s = ls.score_check("按 user_id 去重", self._spec(), "must_include", None)
        self.assertAlmostEqual(s, 0.5, places=6)

    def test_relaxed_mode_can_only_raise_or_equal(self):
        """同一段文本，放宽后的覆盖率不可能低于精确口径。"""
        text = "分母是全部自然新注册用户，并按 user_id 去重"
        exact = ls.score_check(text, self._spec(), "must_include", None)
        relaxed = ls.score_check(text, self._spec(), "must_include", 0.6)
        self.assertGreaterEqual(relaxed, exact)

    def test_full_relaxation_destroys_discrimination(self):
        """**这条是工具那个否证结论的机制**：门槛松到两臂都过，Δ 必然为 0。

        Dev 席在阈值 0.9 上实测就是 Δ=0.00、sd=0.00 —— 检查不再测量任何东西。
        用合成数据把这个机制钉住，说明那不是数据巧合而是结构必然。
        """
        spec = self._spec()
        strong = "分母是全部新注册用户作为分母，按 user_id 去重"
        weak = "分母是全部自然新注册用户，用户去重按 user_id"
        # 精确口径下两臂有差
        self.assertGreater(
            ls.score_check(strong, spec, "must_include", None),
            ls.score_check(weak, spec, "must_include", None),
        )
        # 放到很松之后两臂都满分 → 差为 0
        a = ls.score_check(strong, spec, "must_include", 0.4)
        b = ls.score_check(weak, spec, "must_include", 0.4)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a, 1.0, places=6)

    def test_lead_with_only_looks_at_head(self):
        spec = {"type": "lead_with", "within_chars": 10,
                "groups": [{"label": "结论", "any": ["结论"]}]}
        self.assertAlmostEqual(
            ls.score_check("结论先行：不上线", spec, "lead_with", None), 1.0, places=6)
        self.assertAlmostEqual(
            ls.score_check("x" * 40 + "结论", spec, "lead_with", None), 0.0, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
