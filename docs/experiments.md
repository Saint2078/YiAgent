# Experiments · XSCT 快照

本页固定公开 README 中的数字来源口径，便于复现与审阅。

## 设置

| 项 | 值 |
|----|-----|
| 题源 | [XSCT Bench](https://xsct.ai/gallery) |
| 题 | `l_criticalthinking_059` · `l_agent_006` · `l_write_005_v2`（均 basic） |
| A | 原题 system / 多轮 messages，不注入基因槽 |
| C | Host + G2/G4/G5 分区骨架（非全量 rubric 灌装） |
| 答题模型 | `k3-256k`（Kimi 3）与 `kimi-k2.6` |
| 裁判 | `k3-256k` + 百分制标尺校准（v2） |
| 重复 | 每条件 ×5 |

## 主表（mean / sd）

见根 [`README.md`](../README.md)。

## 逐次分数（原始数列）

### 批判思维 · Kimi 3（简单/复杂 × 基线/基因）

| 条件 | 难度 | scores |
|------|------|--------|
| 基线 A | 简单 basic×5 | `69.9, 35.5, 67.2, 55.5, 85.6` |
| 基因 C | 简单 basic×5 | `94.3, 94.4, 96.3, 93.8, 95.0` |
| 基线 A | 复杂 hard×3 | `63.05, 79.8, 73.3` |
| 基因 C | 复杂 hard×3 | `88.3, 74.4, 83.3` |

图示：[`assets/scores_criticalthinking_kimi3.png`](assets/scores_criticalthinking_kimi3.png)

### 其余题 · Kimi 3 basic

| 题 | A | C |
|----|---|---|
| 任务分解 | `97.5, 96.5, 98.4, 57.0, 93.1` | `97.2, 97.1, 97.3, 93.7, 97.3` |
| 工作汇报 | `92.6, 90.0, 91.8, 92.0, 91.8` | `93.5, 91.7, 94.7, 94.4, 94.7` |

### Kimi 2.6 basic

| 题 | A | C |
|----|---|---|
| 批判思维 | `85.6, 80.4, 78.1, 80.4, 84.0` | `95.5, 96.2, 96.2, 94.6, 93.8` |
| 任务分解 | `92.9, 100, 96.7, 96.7, 69.1` | `97.2, 96.7, 94.2, 96.5, 98.0` |

图示：[`assets/scores_per_trial_kimi3.png`](assets/scores_per_trial_kimi3.png) · [`assets/scores_per_trial_kimi26.png`](assets/scores_per_trial_kimi26.png)

## 反模式对照

「把评分标准整理进提示并替换 system」在工作汇报上综合分 **未稳定超过基线**（告知 ≠ 提升）。  
分区基因骨架是另一条路：稳定边界与规格进 G2/G4，短经验进 G5。

## 工作台研究正本

完整跑次脚本、原始 JSON、联合进化记录仍在工作台项目  
`20260725_基因级Agent方案/`（**不**作为本开源仓默认树）。本仓后续只迁入整理后的可复现包。
