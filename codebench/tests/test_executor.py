# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.executor import run_python

GOLD_CODE = """
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
    return []
"""

GOLD_TESTS = """
assert two_sum([2, 7, 11, 15], 9) == [0, 1]
assert two_sum([3, 2, 4], 6) == [1, 2]
assert two_sum([3, 3], 6) == [0, 1]
"""

BAD_CODE = """
def two_sum(nums, target):
    return [0, 0]
"""


def test_gold_passes():
    r = run_python(GOLD_CODE, GOLD_TESTS, timeout_s=5)
    assert r["ok"] is True, r
    assert r["timed_out"] is False


def test_bad_fails():
    r = run_python(BAD_CODE, GOLD_TESTS, timeout_s=5)
    assert r["ok"] is False
    assert r["timed_out"] is False


def test_timeout():
    r = run_python("while True: pass\n", "assert True\n", timeout_s=1)
    assert r["ok"] is False
    assert r["timed_out"] is True


if __name__ == "__main__":
    test_gold_passes()
    test_bad_fails()
    test_timeout()
    print("ALL_OK")
