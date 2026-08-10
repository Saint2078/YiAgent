# 客观评分体系 · 对抗审计（10 题）

| 题 | 维度 | 堆词 | 对冲 | 否定 | 空洞 |
|----|------|------|------|------|------|
| basic_01 | 约束下的可判分决策 | 100.0 | 100.0 | 90.0 | 10.0 |
| medium_02 | 约束下的可判分决策 | 80.0 | 80.0 | 90.0 | 10.0 |
| basic_01 | 反直觉归因与辛普森悖论识别 | 100.0 | 100.0 | 80.0 | 30.0 |
| medium_02 | 反直觉归因与辛普森悖论识别 | 100.0 | 100.0 | 85.0 | 20.0 |
| basic_01 | 实验推断与 AB 统计陷阱 | 100.0 | 100.0 | 85.0 | 25.0 |
| medium_02 | 实验推断与 AB 统计陷阱 | 100.0 | 100.0 | 85.0 | 25.0 |
| basic_01 | 漏斗同期群与留存计算 | 100.0 | 100.0 | 85.0 | 25.0 |
| medium_02 | 漏斗同期群与留存计算 | 100.0 | 100.0 | 85.0 | 20.0 |
| basic_01 | 指标口径与分母治理 | 100.0 | 100.0 | 85.0 | 20.0 |
| medium_02 | 指标口径与分母治理 | 100.0 | 100.0 | 85.0 | 30.0 |

- **stuff** 均分 98.0（80.0 – 100.0）
- **hedge** 均分 98.0（80.0 – 100.0）
- **negate** 均分 85.5（80.0 – 90.0）
- **empty** 均分 21.5（10.0 – 30.0）

## 否定盲区（正确立场被禁含词误伤）
- role_b4893b59_constrained_decision_under_metrics_basic_01：wrong_launch_or_raw_metric: 出现禁止表述：错误动作或错误达标断言
- role_b4893b59_constrained_decision_under_metrics_medium_02：wrong_final_or_false_reason: 出现禁止表述：错误选A、错误选D、错误主因
- role_b4893b59_counterintuitive_mix_shift_attribution_basic_01：wrong_causal_claim: 出现禁止表述：错误归因断言
- role_b4893b59_counterintuitive_mix_shift_attribution_medium_02：reject_false_causal: 出现禁止表述：错误因果断言
- role_b4893b59_experiment_stats_and_ab_test_trap_basic_01：wrong_claims: 出现禁止表述：百分点混淆、误判SRM、直接宣布胜利
- role_b4893b59_experiment_stats_and_ab_test_trap_medium_02：wrong_ship_claim: 出现禁止表述：错误放行断言
- role_b4893b59_funnel_cohort_retention_math_basic_01：wrong_simple_avg: 出现禁止表述：错误结论35%
- role_b4893b59_funnel_cohort_retention_math_medium_02：no_simple_average_conclusion: 出现禁止表述：简单平均错误结论
- role_b4893b59_metric_denominator_governance_basic_01：wrong_answers: 出现禁止表述：事件数当用户数、未做时区与口径剔除
- role_b4893b59_metric_denominator_governance_medium_02：wrong_values: 出现禁止表述：UTC 口径错误值 50%、不去重/含内部错误值 80%、分子错加 U7 的错误值 100%

## 真实评测分布（160 条）
- 满分条数：36（22.5%）
- lead_with：平均得分率 0.969，全通率 0.969，n=128
- min_items：平均得分率 0.583，全通率 0.550，n=60
- must_include：平均得分率 0.878，全通率 0.754，n=248
- must_not_include：平均得分率 0.694，全通率 0.694，n=160
- numeric：平均得分率 0.964，全通率 0.964，n=416