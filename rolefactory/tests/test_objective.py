"""客观打分器自测。无需 pytest：python -m tests.test_objective（在 /srv 或 rolefactory 目录下）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import objective  # noqa: E402

FAILS: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        FAILS.append(f"{name}: got={got!r} want={want!r}")


def approx(name: str, got: float, want: float, tol: float = 0.01) -> None:
    if got is None or abs(got - want) > tol:
        FAILS.append(f"{name}: got={got!r} want≈{want!r}")


# ---- 数值断言 ----
n_pct = {"type": "numeric", "id": "conv", "weight": 40, "target": 25.0, "tolerance": 0.1,
         "unit": "%", "near": ["转化率"]}
check("百分数直给", objective.score_answer("整体转化率为 25% 左右。", [n_pct])["total"], 100.0)
check("小数等价", objective.score_answer("转化率 0.25。", [n_pct])["total"], 100.0)
check("全角数字", objective.score_answer("转化率２５％。", [n_pct])["total"], 100.0)
check("算错", objective.score_answer("转化率 30%。", [n_pct])["total"], 0.0)
check("没提到定位词", objective.score_answer("结果是 25%。", [n_pct])["total"], 0.0)

n_wan = {"type": "numeric", "id": "gmv", "weight": 10, "target": 12000.0, "tolerance": 1, "near": ["GMV"]}
check("万单位换算", objective.score_answer("GMV 约 1.2万元。", [n_wan])["total"], 100.0)
n_comma = {"type": "numeric", "id": "dau", "weight": 10, "target": 1234567.0, "tolerance": 1, "near": ["DAU"]}
check("千分位", objective.score_answer("DAU 为 1,234,567。", [n_comma])["total"], 100.0)

# ---- 必含 / 禁含 ----
inc = {"type": "must_include", "id": "trap", "weight": 30, "groups": [
    {"label": "分母口径", "any": ["分母", "口径"]},
    {"label": "辛普森", "any": ["辛普森", "simpson", "分层后反转"]},
    {"label": "时间窗", "any": ["时间窗", "统计周期"]},
]}
approx("必含部分分", objective.score_answer("要先确认分母口径。", [inc])["total"], 100 / 3)
check("必含全中", objective.score_answer("分母口径要对齐，注意辛普森悖论，并统一时间窗。", [inc])["total"], 100.0)

exc = {"type": "must_not_include", "id": "wrong", "weight": 20, "groups": [
    {"label": "错误结论", "any": ["因此可以断定改版导致", "转化率 30%"]}]}
check("禁含未犯", objective.score_answer("改版与转化下降相关，但不能断定因果。", [exc])["total"], 100.0)
check("禁含命中", objective.score_answer("因此可以断定改版导致下降。", [exc])["total"], 0.0)

# ---- 回问 / 条数 / 结论先行 ----
ask = {"type": "ask_back", "id": "ask", "weight": 10, "groups": [{"label": "缺口径", "any": ["口径"]}]}
check("回问带问号", objective.score_answer("能否确认这里的口径？", [ask])["total"], 100.0)
approx("提到但未问", objective.score_answer("这里口径不明。", [ask])["total"], 50.0)
check("完全没提", objective.score_answer("直接给结论。", [ask])["total"], 0.0)

items = {"type": "min_items", "id": "n", "weight": 10, "min": 3}
check("枚举够数", objective.score_answer("- a\n- b\n- c\n", [items])["total"], 100.0)
approx("枚举不够", objective.score_answer("1. a\n2. b\n", [items])["total"], 200 / 3)

lead = {"type": "lead_with", "id": "lead", "weight": 10,
        "groups": [{"label": "结论先行", "any": ["结论"]}], "first_chars": 40}
check("结论在前", objective.score_answer("结论：应该回滚。理由如下。", [lead])["total"], 100.0)
check("结论太后", objective.score_answer("x" * 60 + "结论：应该回滚。", [lead])["total"], 0.0)

# ---- 加权合成 ----
mix = objective.score_answer("转化率 25%，要先对齐分母口径。", [n_pct, inc, exc])
approx("加权总分", mix["total"], (1.0 * 40 + (1 / 3) * 30 + 1.0 * 20) / 90 * 100, 0.01)
check("明细条数", len(mix["checks"]), 3)

# ---- 出题自校 ----
approx("算式求值", objective.safe_eval("(1200-900)/1200*100"), 25.0)
approx("百分号转换", objective.safe_eval("2000*15%"), 300.0)
try:
    objective.safe_eval("__import__('os').system('x')")
    FAILS.append("safe_eval 未拦截危险表达式")
except Exception:
    pass

good_case = {
    "messages": [{"role": "user", "content": "上周下单 1200，支付 900，客单价 250 元，退款率 4%，问支付成功率。"}],
    "checks": [
        {"type": "numeric", "id": "pay", "weight": 50, "target": 75.0, "tolerance": 0.5,
         "unit": "%", "computation": "900/1200*100"},
        {"type": "must_not_include", "id": "bad", "weight": 20, "groups": [{"label": "错值", "any": ["25%"]}]},
    ],
}
ok, problems = objective.verify_case(good_case)
check("自校通过", (ok, problems), (True, []))

bad_case = {
    "messages": [{"role": "user", "content": "下单 1200，支付 900，客单价 250。"}],
    "checks": [
        {"type": "numeric", "id": "pay", "weight": 50, "target": 80.0, "tolerance": 0.5,
         "computation": "900/1200*100"},
        {"type": "must_not_include", "id": "bad", "weight": 20, "groups": [{"label": "错值", "any": ["25%"]}]},
    ],
}
ok2, problems2 = objective.verify_case(bad_case)
check("target 不自洽被抓出", ok2, False)
if not any("不一致" in p for p in problems2):
    FAILS.append(f"自校未报出不一致：{problems2}")

if FAILS:
    print("FAILED:")
    for f in FAILS:
        print(" -", f)
    raise SystemExit(1)
print("objective scorer: all checks passed")
