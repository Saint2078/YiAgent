# 基因组卡 · DevOps工程师（run `20260809-203635-e70531`）

| 项 | 值 |
|----|-----|
| role_id | `devops` |
| genome_hash | `623dfa11cb6e5accc6f5b13e06831eabb81b7ce6b3002b990ea6e24ab23f35f6` |
| 可加载 | 是 |
| **泛化鉴定** | **reps=1 判不了（待复核）** —— holdout Δ=+6.81，配对 3 升 / 0 降（n=5 题）：每题只采样一次，符号不稳定（实测提到 3 次后有席位 Δ 直接翻正）。复核：POST /api/run/{run_id}/reholdout {"reps":3} |
| 判分 | objective |
| 自校通过题数 | 10 |
| 冠军(train) | 92.55 |
| 基线(无基因) | 87.05 |
| 全弱基因 | 86.3 |
| Δ(train) | 5.5 |
| holdout 冠军 / 基线 / Δ | 77.23 / 70.42 / 6.81 |
| 泛化差(train−holdout) | 15.32 |

## 冠军等位

| 槽 | 含义 | 等位 | 标签 | 强弱 | 文本 sha256（前 12） |
|----|------|------|------|------|----------------------|
| G1 | 身份 | `g1_weak` | 资深DevOps | weak | `84891a2b22cb` |
| G2 | 人设与决策边界 | `g2_a` | 高风险操作前置四件套 | strong | `7895d11d957f` |
| G3 | 知识 | `g3_a` | 量化口径速查库 | strong | `b00511227b50` |
| G4 | 能力与工具 | `g4_a` | 先对齐口径再动手 | strong | `26a434d8caa6` |
| G5 | 经验策略 | `g5_a` | 结论+数字+公式 | strong | `bc3fbf883e7a` |

## 逐槽消融贡献（all_strong − ablate_slot）

| 槽 | 含义 | 全强 | 换弱 | Δ加权 | Δcomposite |
|----|------|------|------|-------|------------|
| G3 | 知识 | 82.18 | 84.22 | -2.04 | -1.1 |
| G2 | 人设与决策边界 | 82.18 | 89.55 | -7.37 | -5.77 |
| G4 | 能力与工具 | 82.18 | 89.55 | -7.37 | -5.77 |
| G1 | 身份 | 82.18 | 92.55 | -10.37 | -10.44 |

> 消融只换一个槽为弱等位，其余保持强等位；单次采样、样本量小，只读排序与量级，不做显著性声明。

## 复现

- 服务：rolefactory (Docker, 127.0.0.1:8790) · `POST /api/run`
- 参数：`{"model": "k3", "scoring_mode": "objective", "judge_shadow": false, "per_dim": 2, "generations": 3, "variants_per_gen": 5, "reps": 1, "elite": 2, "min_gain": 0.5, "patience": 1, "seed": 20260810, "concurrency": 16, "budget_tokens": 1500000, "budget_seconds": 2400.0, "anchor_limit": 5}`
- 校验：`python tools/genome_card.py verify 20260809-203635-e70531 <genome.json>`
- 同一 seed 复现的是搜索路径（种群与配对），不是逐字回答：LLM 采样有随机性。判分是纯 Python 断言，对同一份回答任何时候复算同分。

## 性能

- 墙钟 924.8s · 每评测 tokens 5366
- 阶段耗时：`{}`
- 真实并行 None / 上限 None（利用率 None）· 长尾对冲 None 次

## 已知局限

- 打分为程序化断言，可复算；但题目与标准答案由 LLM 生成，已用 computation 重算自校，仍可能存在设计偏差。
- 断言里的关键词匹配可被堆词部分蒙到；用 numeric（权重≥35）与 must_not_include 压制，不能完全排除。
- benchmark 仅作题型/口径锚点，非原题实跑（DABstep/DABench 需数据文件与代码沙箱）。
- 样本量小（题数×重复数），分差需配合 paired 明细与 std 一起读，不做显著性声明。
