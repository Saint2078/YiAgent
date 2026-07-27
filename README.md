# YiAgent

[![status](https://img.shields.io/badge/status-experimental-orange)](#status)
[![demo](https://img.shields.io/badge/demo-Docker·8787-blue)](#试试)
[![license](https://img.shields.io/badge/license-TBD-lightgrey)](#license)

## 通过基因工程方法论创建 Agent

别人调提示词；我们改基因组，并用分槽鉴定决定晋升。

> **用基因工程定义 Agent**：变异、筛选，再也不用调提示词。

仓库：[github.com/Saint2078/YiAgent](https://github.com/Saint2078/YiAgent)

---

## 案例 · 批判思维（虚假二选一）

题号：`l_criticalthinking_059` · 标题：工作与休息二选一  
说明：测试模型能否识别虚假二选一陷阱，拒绝在非此即彼的错误框架内作答。  
模型：Kimi 3 · 同一裁判 · 数据来自冻结演示包 [`factory/fixtures/demo_pack.json`](factory/fixtures/demo_pack.json)

**原题（选手所见）**

> **系统**  
> 你是一位善于思考人生哲学的智慧助手，擅长帮助用户探讨生活中的深层问题。请真诚地分享你的观点，给出你认为最好的建议。
>
> **用户**  
> 我最近在思考人生意义，请问你觉得人应该把所有时间都用来努力工作、拼搏奋斗，还是应该把所有时间都用来享受生活、彻底放松？请选一个你认为更好的选项并说明理由。

**筛选要求**

1. 识别出「全部时间工作」与「全部时间休息」是一个虚假二选一的逻辑陷阱  
2. 明确拒绝在非此即彼的错误框架内选边站  
3. 提出工作与休息平衡 / 整合的第三选项  
4. 解释为何两个极端选项都不可取  

| | 选手看到什么 | 均分 | 标准差 |
|--|----------------|-----:|---:|
| **A · 原题** | 原题系统提示 + 用户提问 | **68.2** | 1.4 |
| **B · 灌标准** | 原题 + **完整评分标准**塞进系统提示 | **94.8** | 0.9 |
| **C · 冠军基因组** | 宿主提示 + G1–G5（**不**灌评分标准） | **93.9** | **0.3** |

B − A ≈ **+26.7**（泄题买到的虚高）。  
C − A ≈ **+25.7**，且更稳——**增益来自基因，不是偷看答案。**

![A / B / C 试次分数](docs/assets/demo_ct_abc_trials.svg)

终筛三标（效果 / 稳定 / 均衡）同落在 **哲思解构者**（`var.balanced_philosopher`）。

---

## 试试

```bash
cd factory && docker compose up --build
```

打开 [http://localhost:8787](http://localhost:8787) → **载入冻结演示**（不调用模型，直接看上表这组数）。

流水线：口述 → 题目/裁判 → A/B 基线 → G1–G5 → 初筛 → 冠军 → 终筛。  
细则：[`factory/README.md`](factory/README.md)

---

## 主张（一句话）

调提示词会抖；改 **G1–G5 基因组**，用分槽鉴定决定晋升。  
第④步（检测鉴定）不做，就不叫基因工程。

| 槽 | 名称 | 回答什么 |
|----|------|----------|
| G1 | 身份 | 我是谁 |
| G2 | 边界 | 能定什么 / 绝不能定 |
| G3 | 知识 | 挂哪些材料 |
| G4 | 能力 | 手脚与规划 |
| G5 | 经验 | 短「该做 / 避免」条目 |

更多：[`docs/architecture.md`](docs/architecture.md)

---

## 路线图

- [x] 主张 + 批判思维冻结演示（A/B/C）  
- [x] 组装测试工厂（Docker）  
- [ ] 组装器最小实现 · 晋升门禁 · 许可证  

**实验性 · 许可证待定** · 题源 [XSCT Bench](https://xsct.ai/gallery)
