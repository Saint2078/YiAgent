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

## 反模式对照

「把评分标准整理进提示并替换 system」在工作汇报上综合分 **未稳定超过基线**（告知 ≠ 提升）。  
分区基因骨架是另一条路：稳定边界与规格进 G2/G4，短经验进 G5。

## 工作台研究正本

完整跑次脚本、原始 JSON、联合进化记录仍在工作台项目  
`20260725_基因级Agent方案/`（**不**作为本开源仓默认树）。本仓后续只迁入整理后的可复现包。
