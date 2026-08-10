# 基因组卡 · 软件开发工程师（run `20260809-201229-aa45e1`）

| 项 | 值 |
|----|-----|
| role_id | `role_cbf11840` |
| genome_hash | `eb8422af9b560b6cad4e9e34574c0e2df6acd73cff2d5c7404446139bbda67cc` |
| 可加载 | 是 |
| **泛化鉴定** | **判不了（区间跨 0）** —— 配对Δ均值=-0.87 95%CI[-2.28, +0.4]（n=6 题 × 3 次）：换一组题就可能翻符号，需加题量或重复次数 |
| 判分 | objective |
| 自校通过题数 | 12 |
| 冠军(train) | 93.12 |
| 基线(无基因) | 85.62 |
| 全弱基因 | 90.12 |
| Δ(train) | 7.5 |
| holdout 冠军 / 基线 / Δ | 94.38 / 95.34 / -0.96 |
| 泛化差(train−holdout) | 2.62 |
| holdout 来源 | **复核**（`reholdout.json`，采样更足）；原 run 那次 reps=1 得 Δ=-3.12 |
| ⚠ 打分口径 | train 用 v1、holdout 用 v3 —— **两把尺子**，`泛化差(train−holdout)` 不可直接相减（口径差异见 PERF.md §12） |

## 冠军等位

| 槽 | 含义 | 等位 | 标签 | 强弱 | 文本 sha256（前 12） |
|----|------|------|------|------|----------------------|
| G1 | 身份 | `g1_weak` | 泛泛负责 | weak | `e1611e9d857c` |
| G2 | 人设与决策边界 | `g2_b` | 陷阱前提复述 | strong | `09c2cd12fcea` |
| G3 | 知识 | `g3_a` | 缺陷闭环 | strong | `800cc7b7cc4e` |
| G4 | 能力与工具 | `g4_weak` | 按步来 | weak | `bf6d52ea120c` |
| G5 | 经验策略 | `g5_a` | 结论先行 | strong | `6fffced269f9` |

## 逐槽消融贡献（all_strong − ablate_slot）

| 槽 | 含义 | 全强 | 换弱 | Δ加权 | Δcomposite |
|----|------|------|------|-------|------------|
| G2 | 人设与决策边界 | 86.88 | 84.25 | +2.63 | +10.67 |
| G3 | 知识 | 86.88 | 85.25 | +1.63 | +7.97 |
| G1 | 身份 | 86.88 | 88.62 | -1.74 | -0.65 |
| G4 | 能力与工具 | 86.88 | 90.38 | -3.5 | -4.44 |

> 消融只换一个槽为弱等位，其余保持强等位；单次采样、样本量小，只读排序与量级，不做显著性声明。

## 复现

- 服务：rolefactory (Docker, 127.0.0.1:8790) · `POST /api/run`
- 参数：`{"model": "k3", "scoring_mode": "objective", "judge_shadow": false, "per_dim": 2, "generations": 3, "variants_per_gen": 5, "reps": 1, "elite": 2, "min_gain": 0.5, "patience": 1, "seed": 20260810, "concurrency": 16, "budget_tokens": 1500000, "budget_seconds": 2400.0, "anchor_limit": 5}`
- 校验：`python tools/genome_card.py verify 20260809-201229-aa45e1 <genome.json>`
- 同一 seed 复现的是搜索路径（种群与配对），不是逐字回答：LLM 采样有随机性。判分是纯 Python 断言，对同一份回答任何时候复算同分。

## 性能

- 墙钟 1531.7s · 每评测 tokens 3504
- 阶段耗时：`{}`
- 真实并行 None / 上限 None（利用率 None）· 长尾对冲 None 次

## 已知局限

- 打分为程序化断言，可复算；但题目与标准答案由 LLM 生成，已用 computation 重算自校，仍可能存在设计偏差。
- 断言里的关键词匹配可被堆词部分蒙到；用 numeric（权重≥35）与 must_not_include 压制，不能完全排除。
- benchmark 仅作题型/口径锚点，非原题实跑（DABstep/DABench 需数据文件与代码沙箱）。
- 样本量小（题数×重复数），分差需配合 paired 明细与 std 一起读，不做显著性声明。
