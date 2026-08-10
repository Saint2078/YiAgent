"""配对差值统计自测：自助置信区间与泛化判定。

全程离线，不发请求。运行：python -m tests.test_stats（在 rolefactory 目录下）。

这里守的是一条纪律：holdout 只有 5–6 题，`mean_delta` 的点估计不足以宣称优劣，
必须让区间说话；区间跨 0 就得判「判不了」，不许当赢。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from app.pipeline import bootstrap_ci, paired_delta  # noqa: E402
from genome_card import verdict  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        FAILS.append(f"{name}{': ' + detail if detail else ''}")


# ---- 自助区间 ----

# 样本太少给不出区间，宁可返回 None 也不假装有结论
check("n<3 不给区间", bootstrap_ci([1.0, 2.0]) is None)

# 全正且离 0 远 → 区间应整体在 0 以上
ci = bootstrap_ci([8.0, 9.0, 10.0, 11.0, 12.0, 9.5])
check("一致为正 → 下界 > 0", ci is not None and ci[0] > 0, f"ci={ci}")

# 全负 → 区间应整体在 0 以下
ci = bootstrap_ci([-8.0, -9.0, -10.0, -11.0, -12.0, -9.5])
check("一致为负 → 上界 < 0", ci is not None and ci[1] < 0, f"ci={ci}")

# 均值为正但方向混乱 → 区间必须跨 0（这正是 holdout 现状，不许判赢）
ci = bootstrap_ci([20.0, -15.0, 18.0, -16.0, 2.0, -6.0])
check("方向混乱 → 区间跨 0", ci is not None and ci[0] < 0 < ci[1], f"ci={ci}")

# 同一输入固定 seed → 可复算
check("可复算", bootstrap_ci([3.0, -1.0, 5.0, 0.5, 2.0]) == bootstrap_ci([3.0, -1.0, 5.0, 0.5, 2.0]))

# 区间必须含住点估计
diffs = [4.0, -2.0, 7.0, 1.0, 3.0, -1.0]
ci = bootstrap_ci(diffs)
mean = sum(diffs) / len(diffs)
check("区间含点估计", ci is not None and ci[0] <= mean <= ci[1], f"ci={ci} mean={mean}")


# ---- paired_delta 字段 ----

champ = {"by_case": {f"c{i}": v for i, v in enumerate([90.0, 80.0, 95.0, 70.0, 88.0, 92.0])}}
base = {"by_case": {f"c{i}": v for i, v in enumerate([70.0, 82.0, 75.0, 72.0, 60.0, 70.0])}}
pd = paired_delta(champ, base)
check("配对题数", pd["cases"] == 6, str(pd))
check("有区间", isinstance(pd.get("mean_delta_ci95"), list), str(pd))
check("有标准差", pd.get("sd_delta") is not None, str(pd))
check("significant 是布尔", isinstance(pd.get("significant"), bool), str(pd))
check("无交集时不崩", paired_delta({"by_case": {"a": 1.0}}, {"by_case": {"b": 2.0}})["cases"] == 0)


# ---- 泛化判定 ----

# 区间整体在 0 以上 → 站得住
v = verdict({"delta_train_weighted": 8.0},
            {"delta_weighted": 9.0, "reps": 3,
             "paired": {"cases": 6, "improved": 5, "regressed": 0, "mean_delta": 9.0,
                        "mean_delta_ci95": [4.0, 14.0]}})
check("区间为正 → 站得住", v["generalizes"] is True, str(v))

# 区间跨 0 但 Δ 为正 → 必须判「判不了」，不许当赢
v = verdict({"delta_train_weighted": 8.0},
            {"delta_weighted": 3.0, "reps": 3,
             "paired": {"cases": 6, "improved": 3, "regressed": 2, "mean_delta": 3.0,
                        "mean_delta_ci95": [-6.0, 12.0]}})
check("区间跨 0 → 判不了", v["generalizes"] is None and "跨 0" in v["label"], str(v))

# 区间整体在 0 以下 → 明确未通过
v = verdict({"delta_train_weighted": 8.0},
            {"delta_weighted": -5.0, "reps": 3,
             "paired": {"cases": 6, "improved": 0, "regressed": 5, "mean_delta": -5.0,
                        "mean_delta_ci95": [-11.0, -1.0]}})
check("区间为负 → 未通过", v["generalizes"] is False, str(v))

# reps=1 且无区间 → 一律不给定论（符号本身不稳定，实测会翻）
v = verdict({"delta_train_weighted": 8.0},
            {"delta_weighted": -2.74, "paired": {"cases": 6, "improved": 1, "regressed": 2}})
check("reps=1 → 判不了", v["generalizes"] is None and "reps=1" in v["label"], str(v))

# reps=1 时哪怕 Δ 很正也不许判赢（DevOps 那种 3 升 0 降的漂亮数也一样）
v = verdict({"delta_train_weighted": 5.5},
            {"delta_weighted": 6.81, "reps": 1,
             "paired": {"cases": 5, "improved": 3, "regressed": 0}})
check("reps=1 且 Δ 为正 → 仍判不了", v["generalizes"] is None, str(v))

# reps≥2 但无区间 → 退回粗判，且 reason 要注明
v = verdict({"delta_train_weighted": 8.0},
            {"delta_weighted": -2.74, "reps": 3,
             "paired": {"cases": 6, "improved": 1, "regressed": 2}})
check("无区间 → 粗判", v["generalizes"] is False and "粗判" in v["reason"], str(v))

# 没有 holdout → 未鉴定，不能崩
check("无 holdout", verdict({}, {})["label"] == "未鉴定")


if FAILS:
    print(f"FAIL {len(FAILS)}")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("test_stats OK")
