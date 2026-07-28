# Architecture · G1–G5

YiAgent 把 Agent 配置拆成五个高级基因类别，对应生物学「染色体分区」：变哪一区，评分体系应能单独归因。

| 槽 | 英文键 | 一句话 | 变异优先级 |
|----|--------|--------|------------|
| **G1** | `identity` | 我是谁、对外怎么自报 | 低（变则几乎换角色） |
| **G2** | `persona` | 风格 / 职责 / 能定什么 / 绝不能定 | 中高 |
| **G3** | `knowledge` | 长期以哪些已认证材料为据 | 中 |
| **G4** | `capability` | 这班允许用什么手脚、怎么规划 | 高 |
| **G5** | `experience` | 失败/成功蒸馏的短控制信号（含 AVOID） | 高（叠加层） |

## Skills · 外部带基因的工具（基因盒）

Skills **不是第六条染色体**。它们是可插拔的 **基因盒（gene cassette）**：

| 携带物 | 说明 |
|--------|------|
| 等位片段 | 只注入 **G3 / G4 / G5**（不改写核心 G1/G2） |
| 外部工具 | OpenAI function 规格 + 可选 `gene_hint`（该工具的程序叠层） |
| 可选 handler | `builtin:…` 或后续外挂实现 |

```
Genome = base(G1+G2) + layers(G3+G4) + overlays(G5[])
system = Assemble(Genome + SkillCassettes[])
tools  = CoreTools ∪ SkillTools
```

变体字段：`variant.skills: ["skill.workspace_notes", …]`；CLI：`--skill skill.id`（可重复）。

示例包：`src/yiagent/genome/data/skills/workspace_notes.json`。

## 组装公式

```
Genome = base(G1 + G2) + layers(G3 + G4) + overlays(G5[])
system = Assemble(Genome + Skills)   # 或 Host + 分区叠加，取决于宿主策略
```

## 四步流水线

1. **取基因** — 定义各槽等位基因（含 Skill 盒内片段）  
2. **组装载体** — `Assemble` + 可观测标记  
3. **导入** — 装入运行时（核心工具 + Skill 工具）  
4. **检测鉴定** — 分槽打分 + 晋升门禁（不可省略）

## 设计纪律

- 边界进 G2，产出规格进 G4，经验进 G5；禁止用 G5 偷运整份作业说明书  
- Skills 只扩 G3–G5 + 工具，禁止借 Skill 改写 G1/G2  
- 禁止把完整评分标准 / rubric 灌进任一槽（静态灌装反模式）  
- **评分门禁规则不进选手基因组**（裁判不能住在选手里）

## 明确不进基因组

任务卡正文、团队交接协议、观测仪器通道、宿主机器 / Docker 部署环境。
