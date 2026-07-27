# YiAgent

[![status](https://img.shields.io/badge/status-experimental-orange)](#status)
[![demo](https://img.shields.io/badge/demo-Docker·8787-blue)](#试试)
[![license](https://img.shields.io/badge/license-TBD-lightgrey)](#license)

## 别人调 Prompt。我们改基因组。

*They tune prompts. We edit the genome — and promote only with a slot-level verdict.*

调一句提示词，分数会抖、结果会飘。  
YiAgent 把 Agent 当成可进化的生物体：**G1–G5 分槽基因 → 组装 → 导入 → 分槽鉴定决定晋升。**

> 台上短钩：**用基因工程定义 Agent**——变异、筛选，再也不用调 Prompt。

仓库：[github.com/Saint2078/YiAgent](https://github.com/Saint2078/YiAgent)

---

## 一图看懂：地板 · 天花板 · 基因

同一题、同一裁判，三组对照：

| | 选手看到什么 | 它在证明什么 |
|--|----------------|--------------|
| **A · 原题** | 原题 system + user | **地板**：无标准泄露 |
| **B · 灌标准** | 原题 + **完整评分标准**塞进 system | **天花板**：教考同一套（反模式） |
| **C · 基因组** | 原题 host + **G1–G5**（**不**灌标准） | **主线**：相对 A 的增益与稳定性 |

裁判始终持有 `criteria`；正式筛选时标准**绝不进**选手基因组。  
成功标准不是「追上 B」，而是：**不泄题，也能抬分、收波动。**

### 冻结演示 · 批判思维（可点开复现）

一次完整流水线快照（Kimi 3 · n=5 / 终筛 n=5）：

| 条件 | mean | sd | 读法 |
|------|-----:|---:|------|
| **A** 原题对照 | **68.2** | 1.4 | 地板 |
| **B** 灌入完整标准 | **94.8** | 0.9 | 泄露上界 |
| **C** 冠军基因组（终筛） | **93.9** | **0.3** | 不泄题，逼近 B，且更稳 |

B − A ≈ **+26.7**（泄题能买到的虚高）。  
冠军基因组相对 A ≈ **+25.7**，波动更小——**增益来自基因，不是来自偷看答案。**

```bash
cd factory && docker compose up --build
# → http://localhost:8787  →  「载入冻结演示」
```

原始包：[`factory/fixtures/demo_pack.json`](factory/fixtures/demo_pack.json) · 跑次日志见 [`factory/fixtures/runs/`](factory/fixtures/runs/)

---

## 研究档 · 更多题（A vs C）

同一裁判下，早期 XSCT 快照（基因骨架 Host+G2/G4/G5，**不是**灌标准）：

| 题 | 模型 | A mean | **C mean** | A sd | **C sd** |
|----|------|-------:|-----------:|-----:|---------:|
| 批判思维 | Kimi 3 | 62.7 | **94.8** | 18.6 | **0.96** |
| 任务分解 | Kimi 3 | 88.5 | **96.5** | 17.7 | **1.58** |
| 工作汇报 | Kimi 3 | 91.6 | 93.8 | 0.97 | 1.27 |
| 批判思维 | Kimi 2.6 | 81.7 | **95.3** | 3.03 | **1.05** |
| 任务分解 | Kimi 2.6 | 91.1 | **96.5** | 12.5 | **1.42** |

基线越容易翻车，基因骨架抬分、收窄波动越明显；Kimi 3 / 2.6 方向一致。  
（n=5，中置信；口径见 [`docs/experiments.md`](docs/experiments.md)。）

**批判思维（简单/复杂 × 基线/基因）**

![批判思维 简单复杂×基线基因](docs/assets/scores_criticalthinking_kimi3.png)

**其余题 · Kimi 3** · **Kimi 2.6**

![Kimi 3 其余题](docs/assets/scores_per_trial_kimi3.png)
![Kimi 2.6](docs/assets/scores_per_trial_kimi26.png)

---

## 试试（Docker only）

```bash
cd factory && docker compose up --build
```

打开 [http://localhost:8787](http://localhost:8787)：

1. **载入冻结演示** → 立刻看到 A / B / 基因组终筛（不调模型）  
2. 或填 Key → 口述生成题目 → 跑完整 **7 步筛选台**

流水线：口述 → 题目/裁判 → **A/B 基线** → G1–G5 基因组 → 初筛 → 冠军池 → 终筛（效果 / 稳定 / 均衡）。

细则：[`factory/README.md`](factory/README.md)

---

## 生物学同款流水线

| | 生物学 | YiAgent |
|--|--------|---------|
| ① | 取目的基因 | **G1–G5** 等位基因 |
| ② | 组装载体 | **`Assemble`** |
| ③ | 导入细胞 | 灌进运行时 |
| ④ | **检测鉴定** | **分槽打分 + 晋升门禁** |

第④步不做，就不叫基因工程——只是随机改配置。  
鉴定要答清两句：**该不该晋升？强在哪一段基因？**

### G1–G5

| 槽 | 名称 | 回答什么 | 变异 |
|----|------|----------|------|
| G1 | 身份 `identity` | 我是谁、怎么自报 | 低 |
| G2 | 人设与决策边界 `persona` | 能定什么 / 绝不能定 | 中高 |
| G3 | 知识 `knowledge` | 挂哪些已认证材料 | 中 |
| G4 | 能力与工具 `capability` | 手脚、规划、预算 | 高 |
| G5 | 经验策略 `experience` | 短 DO/AVOID 叠加层 | 高 |

`base(G1+G2) + layers(G3+G4) + overlays(G5[])` · [`docs/architecture.md`](docs/architecture.md)

---

## 结构

```
docs/           # 架构与实验口径
src/yiagent/    # Assemble / 晋升门禁（搭建中）
factory/        # 可点筛选台 · 冻结演示 + 实跑（Docker :8787）
experiments/    # 可复现入口（搭建中）
```

研究实验正本仍在工作台 `20260725_基因级Agent方案/`；本仓为对外开源骨架，`factory/` 是可点 Demo。

---

## 路线图

- [x] 主张：改基因组 + 分槽鉴定晋升  
- [x] 早期 XSCT 数据（A vs C）  
- [x] 组装测试工厂（A/B → 基因组 → 初筛 → 终筛 + 冻结演示）  
- [ ] schema + `Assemble` 最小实现  
- [ ] 晋升 / 驳回 / 噪声不足  
- [ ] 公开晋升榜 · License  

**Experimental · License TBD** · 题源 [XSCT Bench](https://xsct.ai/gallery)
