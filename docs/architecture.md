# Architecture · Genome + Runtime + Context

## 三层（成熟 Agent 正本）

| 层 | 来源 | 作用 | 进基因组？ |
|----|------|------|------------|
| **Genome** | bank variant · G1–G5 + Skills | 可筛选的选手人格（替换 Hermes SOUL） | **是** |
| **Runtime** | 内置 + `$YIAGENT_HOME/RULES.md` | 平台纪律（禁编造、工具用法等） | **否** |
| **Context** | cwd 起向上找 `AGENTS.md` | 项目约定（对齐 Hermes） | **否** |

冲突优先级：**G2 硬边界 > Runtime rules > AGENTS.md**。

```
system = Precedence
       + Assemble(host + G1–G5 + Skills)   # Genome
       + Runtime(rules [, RULES.md])
       + Context(AGENTS.md)
```

## G1–G5

| 槽 | 英文键 | 一句话 | 变异优先级 |
|----|--------|--------|------------|
| **G1** | `identity` | 我是谁、对外怎么自报 | 低（变则几乎换角色） |
| **G2** | `persona` | 风格 / 职责 / 能定什么 / 绝不能定 | 中高 |
| **G3** | `knowledge` | 长期以哪些已认证材料为据 | 中 |
| **G4** | `capability` | 这班允许用什么手脚、怎么规划 | 高 |
| **G5** | `experience` | 失败/成功蒸馏的短控制信号（含 AVOID） | 高（叠加层） |

## Skills · 外部带基因的工具（基因盒）

Skills **不是第六条染色体**。可插拔 **gene cassette**：只注入 **G3/G4/G5** + 可选工具。

## 四步流水线

1. **取基因** — 定义各槽等位基因（含 Skill 盒内片段）  
2. **组装载体** — `Assemble` + Runtime/Context 叠层  
3. **导入** — 装入运行时  
4. **检测鉴定** — 分槽打分 + 晋升门禁（不可省略）

## 改进闭环（Session → Factory）

效果差时：`yiagent improve` 从 CLI session 导出 improve-pack → 工厂 `:8787` 载入种子（跳过 A/B）→ 邻域精炼（固定 G1，主变异 G2/G4/G5）→ 初筛/终筛 → `save/*_best_genome*` → `yiagent improve --apply` 写回 `~/.yiagent`（`agent.bank` + `agent.variant`）。

API：`POST /api/session/load-seed` · `.../genomes/refine` · `POST /api/session/improve-auto`。

## 设计纪律

- 边界进 G2，产出规格进 G4，经验进 G5；禁止用 G5 偷运整份作业说明书  
- Skills 只扩 G3–G5 + 工具，禁止借 Skill 改写 G1/G2  
- **评分 rubric / 平台 Runtime / AGENTS.md 不进选手基因组**  
- 任务卡正文、部署环境、观测通道不进基因组  

## 配置开关（`config.yaml`）

```yaml
runtime:
  rules: true
  rules_file: true
context:
  agents_md: true
```
