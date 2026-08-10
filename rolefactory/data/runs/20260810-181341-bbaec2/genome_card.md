# 基因组卡 · 评测工程师（run `20260810-181341-bbaec2`）

| 项 | 值 |
|----|-----|
| role_id | `role_b2267ae0` |
| genome_hash | `fcd551a11a53be8f82cbec9b891e0b5b51e1e55a96302ccd0150baa0173a839a` |
| 可加载 | 是 |
| **泛化鉴定** | **reps=1 判不了（待复核）** —— holdout Δ=+1.76，配对 2 升 / 2 降（n=6 题）：每题只采样一次，符号不稳定（实测提到 3 次后有席位 Δ 直接翻正）。复核：POST /api/run/{run_id}/reholdout {"reps":3} |
| 判分 | objective |
| 自校通过题数 | 12 |
| 冠军(train) | 91.0 |
| 基线(无基因) | 83.0 |
| 全弱基因 | 83.75 |
| Δ(train) | 8.0 |
| holdout 冠军 / 基线 / Δ | 92.04 / 90.28 / 1.76 |
| 泛化差(train−holdout) | -1.04 |

## 冠军等位

| 槽 | 含义 | 等位 | 标签 | 强弱 | 文本 sha256（前 12） |
|----|------|------|------|------|----------------------|
| G1 | 身份 | `g1_a` | 分数守门人 | strong | `7d1f9c1f1364` |
| G2 | 人设与决策边界 | `g2_a` | 硬边界清单 | strong | `6774248e44d2` |
| G3 | 知识 | `g3_a` | 统计口径手册 | strong | `30eb3ecdcde9` |
| G4 | 能力与工具 | `g4_a` | 先对齐口径再动手 | strong | `97ea7f50be37` |
| G5 | 经验策略 | `g5_a` | 数字必带出身 | strong | `0f2ad9a13cc4` |

## 逐槽消融贡献（all_strong − ablate_slot）

| 槽 | 含义 | 全强 | 换弱 | Δ加权 | Δcomposite |
|----|------|------|------|-------|------------|
| G2 | 人设与决策边界 | 91.0 | 71.13 | +19.87 | +25.92 |
| G1 | 身份 | 91.0 | 76.58 | +14.42 | +25.36 |
| G3 | 知识 | 91.0 | 86.62 | +4.38 | +7.91 |
| G4 | 能力与工具 | 91.0 | 89.37 | +1.63 | +2.23 |

> 消融只换一个槽为弱等位，其余保持强等位；单次采样、样本量小，只读排序与量级，不做显著性声明。

## 复现

- 服务：rolefactory (Docker, 127.0.0.1:8790) · `POST /api/run`
- 参数：`{"model": "k3", "scoring_mode": "objective", "judge_shadow": false, "per_dim": 2, "generations": 3, "variants_per_gen": 5, "reps": 1, "elite": 2, "min_gain": 0.5, "patience": 1, "seed": 20260810, "concurrency": 32, "budget_tokens": 1500000, "budget_seconds": 2400.0, "anchor_limit": 5}`
- 校验：`python tools/genome_card.py verify 20260810-181341-bbaec2 <genome.json>`
- 同一 seed 复现的是搜索路径（种群与配对），不是逐字回答：LLM 采样有随机性。判分是纯 Python 断言，对同一份回答任何时候复算同分。

## 性能

- 墙钟 1279.2s · 每评测 tokens 5465
- 阶段耗时：`{"blueprint": 42.8, "cases": 139.6, "bank": 38.9, "baseline+gen0": 403.1, "evolve": 546.4, "holdout": 108.2}`
- 真实并行 7.36 / 上限 32（利用率 0.23）· 长尾对冲 6 次

## 已知局限

- 打分为程序化断言，可复算；但题目与标准答案由 LLM 生成，已用 computation 重算自校，仍可能存在设计偏差。
- 断言里的关键词匹配可被堆词部分蒙到；用 numeric（权重≥35）与 must_not_include 压制，不能完全排除。
- benchmark 仅作题型/口径锚点，非原题实跑（DABstep/DABench 需数据文件与代码沙箱）。
- 样本量小（题数×重复数），分差需配合 paired 明细与 std 一起读，不做显著性声明。
- 长尾对冲：补发 6 次、其中 0 次由补发先返回；被丢弃那份的服务端 token 未计入本地计量，实际用量略高于报告值。
