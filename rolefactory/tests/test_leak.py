#!/usr/bin/env python3
"""关键词表泄露 numeric 标准答案：清洗必须删得准，且不能删过头。

来由是一次实测：Dev 席有道题，纯堆关键词能拿 **100 分**。查出 `must_include` 的
同义词里直接写着答案（"365"、"第 10 行"），抄关键词 = 连数值分一起白拿。
历史 148 道客观题里 56% 有这个毛病（tools/audit_cases.py）。

处置是**删同义词**而不是把题打回重出，所以这里要钉死两侧边界：
带答案的删掉、不带答案的一个都不许动。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.objective import (  # noqa: E402
    keyword_text,
    leaks_numeric,
    normalize_checks,
    score_answer,
    strip_answer_leaks,
)

NUM = {
    "type": "numeric",
    "id": "n1",
    "weight": 60.0,
    "target": 365.0,
    "tolerance": 1.0,
    "computation": "365",
}


def _mi(*syns: str, weight: float = 40.0) -> dict:
    return {"type": "must_include", "id": "m1", "weight": weight,
            "groups": [{"label": "g", "any": list(syns)}]}


class StripTests(unittest.TestCase):
    def test_removes_synonym_carrying_answer(self):
        out = strip_answer_leaks([NUM, _mi("365 天", "平年天数")])
        kept = [g["any"] for c in out if c["type"] == "must_include" for g in c["groups"]]
        self.assertEqual(kept, [["平年天数"]])

    def test_drops_check_when_all_synonyms_leak(self):
        out = strip_answer_leaks([NUM, _mi("365", "365 天", "共 365 天")])
        self.assertEqual([c["type"] for c in out], ["numeric"])

    def test_keeps_unrelated_numbers(self):
        """题里出现别的数字不算泄题——只有落在答案容差内才算（366 在 365±1 内，故不用它）。"""
        out = strip_answer_leaks([NUM, _mi("12 个月", "第 4 季度")])
        kept = [s for c in out if c["type"] == "must_include" for g in c["groups"] for s in g["any"]]
        self.assertEqual(kept, ["12 个月", "第 4 季度"])

    def test_tolerance_respected(self):
        """容差内视为同一个答案：target=365±1，写 364 也是泄题。"""
        out = strip_answer_leaks([NUM, _mi("364 天", "结论")])
        kept = [s for c in out if c["type"] == "must_include" for g in c["groups"] for s in g["any"]]
        self.assertEqual(kept, ["结论"])

    def test_no_numeric_check_means_no_stripping(self):
        checks = [_mi("365 天", "平年天数")]
        self.assertEqual(strip_answer_leaks([dict(c) for c in checks]), checks)

    def test_must_not_include_never_stripped(self):
        """禁含断言不是「可抄的关键词」，即使写着答案数字也不能删。"""
        spec = {"type": "must_not_include", "id": "x1", "weight": 10.0,
                "groups": [{"label": "禁", "any": ["365 天就能上线"]}]}
        out = strip_answer_leaks([NUM, spec])
        self.assertIn(spec, out)


class LeakDetectionTests(unittest.TestCase):
    def test_flags_leak_before_cleaning(self):
        self.assertEqual(leaks_numeric([NUM, _mi("共 365 天", "结论")]), ["n1"])

    def test_clean_after_normalize(self):
        self.assertEqual(leaks_numeric(normalize_checks([dict(NUM), _mi("共 365 天", "结论")])), [])

    def test_keyword_text_excludes_forbidden(self):
        text = keyword_text([_mi("口径", "定义"),
                             {"type": "must_not_include", "weight": 5, "groups": [{"any": ["可以上线"]}]}])
        self.assertIn("口径", text)
        self.assertNotIn("可以上线", text)


class IdempotenceTests(unittest.TestCase):
    """normalize_checks 必须幂等 —— 打分前会再过一遍（judge.py），不能每过一次就改一次分。

    这条是 holdout 复核的地基：新题在出题期已归一化，复核时再过一遍必须**同分**；
    旧题则被就地纠正，让 `scorer_version` 名副其实。
    """

    def test_twice_equals_once(self):
        once = normalize_checks([dict(NUM), _mi("共 365 天", "平年天数", "结论")])
        twice = normalize_checks([dict(c) for c in once])
        self.assertEqual(twice, once)

    def test_score_stable_across_renormalize(self):
        once = normalize_checks([dict(NUM), _mi("共 365 天", "平年天数", "结论")])
        reply = "结论：平年天数是 365 天。"
        self.assertEqual(
            score_answer(reply, once)["total"],
            score_answer(reply, normalize_checks([dict(c) for c in once]))["total"],
        )


class SoupFloorTests(unittest.TestCase):
    """清洗后「抄关键词」不该再拿到数值分——这是整件事的目的。"""

    def test_soup_cannot_reach_numeric_weight(self):
        checks = normalize_checks([dict(NUM), _mi("共 365 天", "平年天数", "结论")])
        soup = "；".join(
            s for c in checks if c["type"] == "must_include" for g in c["groups"] for s in g["any"]
        )
        got = score_answer(soup, checks)
        # numeric 占 60%，堆词最多拿剩下的 40%
        self.assertLessEqual(float(got["total"]), 40.0 + 1e-6, got)


if __name__ == "__main__":
    unittest.main(verbosity=2)
