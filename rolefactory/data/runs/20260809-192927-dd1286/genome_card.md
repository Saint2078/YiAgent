# 基因组卡 · 项目经理（run `20260809-192927-dd1286`）

| 项 | 值 |
|----|-----|
| role_id | `role_c81cdcf6` |
| genome_hash | `0c446d8b6f994c539e438b8ea7f278c0eeeb5e89f0fac84fec6240e8fd00ba63` |
| 可加载 | 是 |
| **泛化鉴定** | **未通过泛化鉴定** —— holdout Δ=-2.74，配对 1 升 / 2 降（n=6）：train 上的增益（3.82）大概率是过拟合，不能宣称该基因组更强 |
| 判分 | objective |
| 自校通过题数 | 12 |
| 冠军(train) | 87.88 |
| 基线(无基因) | 84.06 |
| 全弱基因 | 83.33 |
| Δ(train) | 3.82 |
| holdout 冠军 / 基线 / Δ | 83.88 / 86.62 / -2.74 |
| 泛化差(train−holdout) | 4.0 |

## 冠军等位

| 槽 | 含义 | 等位 | 标签 | 强弱 | 文本 sha256（前 12） |
|----|------|------|------|------|----------------------|
| G1 | 身份 | `g1_weak` | 空泛定位 | weak | `0bb1c318913f` |
| G2 | 人设与决策边界 | `g2_b` | 过程可复核型 | strong | `9e09b6428e25` |
| G3 | 知识 | `g3_a` | 公式与口径库 | strong | `d5916a61eeb6` |
| G4 | 能力与工具 | `g4_weak` | 空泛流程 | weak | `23b823d1baa7` |
| G5 | 经验策略 | `g5_a` | 数据先行结构 | strong | `c2e6f7325fdb` |

## 逐槽消融贡献（all_strong − ablate_slot）

| 槽 | 含义 | 全强 | 换弱 | Δ加权 | Δcomposite |
|----|------|------|------|-------|------------|
| G2 | 人设与决策边界 | 77.85 | 79.75 | -1.9 | -0.67 |
| G3 | 知识 | 77.85 | 80.94 | -3.09 | -2.99 |
| G1 | 身份 | 77.85 | 83.67 | -5.82 | -7.05 |
| G4 | 能力与工具 | 77.85 | 85.92 | -8.07 | -9.57 |

> 消融只换一个槽为弱等位，其余保持强等位；单次采样、样本量小，只读排序与量级，不做显著性声明。

## 复现

- 服务：rolefactory (Docker, 127.0.0.1:8790) · `POST /api/run`
- 参数：`{"model": "k3", "scoring_mode": "objective", "judge_shadow": false, "per_dim": 2, "generations": 3, "variants_per_gen": 5, "reps": 1, "elite": 2, "min_gain": 0.5, "patience": 1, "seed": 20260810, "concurrency": 16, "budget_tokens": 1500000, "budget_seconds": 2400.0, "anchor_limit": 5}`
- 校验：`python tools/genome_card.py verify 20260809-192927-dd1286 <genome.json>`
- 同一 seed 复现的是搜索路径（种群与配对），不是逐字回答：LLM 采样有随机性。判分是纯 Python 断言，对同一份回答任何时候复算同分。

## 性能

- 墙钟 896.5s · 每评测 tokens 3762
- 阶段耗时：`{}`
- 真实并行 None / 上限 None（利用率 None）· 长尾对冲 None 次

## 已知局限

- 打分为程序化断言，可复算；但题目与标准答案由 LLM 生成，已用 computation 重算自校，仍可能存在设计偏差。
- 断言里的关键词匹配可被堆词部分蒙到；用 numeric（权重≥35）与 must_not_include 压制，不能完全排除。
- benchmark 仅作题型/口径锚点，非原题实跑（DABstep/DABench 需数据文件与代码沙箱）。
- 样本量小（题数×重复数），分差需配合 paired 明细与 std 一起读，不做显著性声明。
