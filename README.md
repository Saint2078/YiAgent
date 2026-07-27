# YiAgent

[![status](https://img.shields.io/badge/status-experimental-orange)](#status)
[![demo](https://img.shields.io/badge/demo-Docker·8787-blue)](#试试)
[![license](https://img.shields.io/badge/license-TBD-lightgrey)](#license)

## 通过基因工程方法论创建AGENT

*They tune prompts. We edit the genome — and promote only with a slot-level verdict.*

> **用基因工程定义 Agent**：变异、筛选，再也不用调 Prompt。

仓库：[github.com/Saint2078/YiAgent](https://github.com/Saint2078/YiAgent)

---

## Case · 批判思维（虚假二选一）

题：`l_criticalthinking_059`「工作与休息二选一」  
模型：Kimi 3 · 同一裁判 · 数据来自冻结演示包 [`factory/fixtures/demo_pack.json`](factory/fixtures/demo_pack.json)

| | 选手看到什么 | mean | sd |
|--|----------------|-----:|---:|
| **A · 原题** | 原题 system + user | **68.2** | 1.4 |
| **B · 灌标准** | 原题 + **完整评分标准**塞进 system | **94.8** | 0.9 |
| **C · 冠军基因组** | host + G1–G5（**不**灌标准） | **93.9** | **0.3** |

B − A ≈ **+26.7**（泄题买到的虚高）。  
C − A ≈ **+25.7**，且更稳——**增益来自基因，不是偷看答案。**

![A / B / C trials](docs/assets/demo_ct_abc_trials.svg)

终筛三标（效果 / 稳定 / 均衡）同落在 **哲思解构者**（`var.balanced_philosopher`）。

---

## 试试

```bash
cd factory && docker compose up --build
```

打开 [http://localhost:8787](http://localhost:8787) → **载入冻结演示**（不调模型，直接看上表这组数）。

流水线：口述 → 题目/裁判 → A/B 基线 → G1–G5 → 初筛 → 冠军 → 终筛。  
细则：[`factory/README.md`](factory/README.md)

---

## 主张（一句话）

调 Prompt 会抖；改 **G1–G5 基因组**，用分槽鉴定决定晋升。  
第④步（检测鉴定）不做，就不叫基因工程。

| 槽 | 名称 | 回答什么 |
|----|------|----------|
| G1 | 身份 | 我是谁 |
| G2 | 边界 | 能定什么 / 绝不能定 |
| G3 | 知识 | 挂哪些材料 |
| G4 | 能力 | 手脚与规划 |
| G5 | 经验 | 短 DO/AVOID |

更多：[`docs/architecture.md`](docs/architecture.md)

---

## 路线图

- [x] 主张 + 批判思维冻结演示（A/B/C）  
- [x] 组装测试工厂（Docker）  
- [ ] `Assemble` 最小实现 · 晋升门禁 · License  

**Experimental · License TBD** · 题源 [XSCT Bench](https://xsct.ai/gallery)
