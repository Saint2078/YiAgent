# Experiments · 批判思维演示口径

公开 README 数字一律来自 factory 冻结包，**只讲这一题**。

| 项 | 值 |
|----|-----|
| 包 | [`factory/fixtures/demo_pack.json`](../factory/fixtures/demo_pack.json) |
| 题 | `l_criticalthinking_059` 工作与休息二选一 |
| 模型 | Kimi 3（`k3`） |
| A | 原题对照 · n=5 · `[67.6, 67.9, 66.8, 70.6, 67.9]` |
| B | 灌入完整评分标准 · n=5 · `[96.0, 94.6, 95.2, 94.6, 93.7]` |
| C | 终筛冠军 `var.balanced_philosopher` · n=5 · `[93.9, 94.4, 93.7, 93.8, 93.7]` |

图：[`assets/demo_ct_abc_trials.svg`](assets/demo_ct_abc_trials.svg)（3 条实线试次 + 6 条虚线 mean±sd）  
再生：`python3 scripts/gen_factory_demo_charts.py`（读 demo_pack，stdlib SVG）。
