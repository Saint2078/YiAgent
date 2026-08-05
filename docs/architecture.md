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

## 组装载体（B1 · 表达载体）

`yiagent.assembly` 把「基因组 JSON → 运行时配置」固化为显式分槽规则（`SLOT_RULES`）：每槽声明来源字段（`variant.slots[Gx]` → `bank.alleles[Gx]`）、运行时挂载点（`system.genome#Gx`）、缺槽行为与校验约束——G1/G2 为必需槽（缺槽 Blocked），G3–G5 缺槽走 `default_skip` 且允许 Skill 基因盒注入。

装配产物是**配置包**（`kind: yiagent.expression_vector`）：`runtime`（host、装配后基因组文本、槽位挂载点、skill 工具）+ `markers`（gene_hash、各槽等位 id/版本、装配时间、校验报告），可 JSON 落盘审计、可复现。校验失败抛 `AssemblyBlocked`（无基因/坏基因不硬组装）；`validate_genome` 为校验钩子（B2A 完整性校验挂接位）。运行时侧 `AgentSession.genome_pack` 持有配置包，构造时发出 `genome_pack` 事件（一行标记见 `marker_line`）。

## 导入受体（B2 · 基因来源 → 可运行配置）

`yiagent.recipient` 把三类基因来源统一收口：本地 bank（`~/.yiagent` 库 JSON）、hof pull 落盘包（`gene_hash` + 内嵌 `bank`）、improve 导出包 / best_genome（`seed` 重建 bank，与 `--apply` 同一口径）。三步显式可审计：`load_gene_source`（识别形态 → 归一 → 接入即过 `validate_genome`）→ `import_genome`（装配 expression_vector 配置包，`markers.source` 留来源痕）→ `save_vector`（落盘 `~/.yiagent/assembled/vector_{gene_hash}.json`）；CLI 入口 `yiagent assemble [source] [--variant] [--out]`。

完整性校验的铁律：`validation.status != "ok"` 一律 `AssemblyBlocked`，禁止静默降级。gene_hash 过严格格式门禁（`hash_format_ok`）：只认名人堂规范 `yg-xxxxxxxx`（8 位小写字母数字）、sha256 64 位小写 hex、种子白名单 `yg-seed-*`（fixtures / improve 种子库形态）；hof 包还要求包声明 hash 与基因组自带 hash 一致。能力清单核对（B2C）：装配产物的 `runtime.skill_tools` 与各槽挂载状态必须与基因声明一致（`capability_checks`），不一致进 `validation.checks` 并 Blocked；基因声明的 Skill 未装载同样 Blocked。

## 表型鉴定与一键组装（B3/B4 · 从基因组到可运行 Agent）

`yiagent.phenotype` 是表型鉴定 harness，分两层（铁律：实跑只能由人触发）：

- **offline 层**（全自动、进单测）：`smoke_checks` 对装配产物做结构检查——
  配置包形态、G1/G2 挂载且正文有实质内容、G2 边界约束进入 system 文本、
  Skill 工具挂载与声明一致、`marker_line` 可输出；`build_checklist`（B3B）
  对照规格一页产出「能做 / 不做 / 越界」checklist（auto 项核声明层，
  wont 项留 live pending 由人打分，说明与样例见 `docs/phenotype-checklist.md`）。
- **live 层**（仅人触发）：`run_live_smoke` 默认拒绝（`confirmed=False` 即抛错），
  只在 CLI `--live` 显式确认后跑一轮真实对话，回传事件流与回答。

CLI 入口 `yiagent smoke <vector.json> [--checklist] [--json] [--live]`。
一键组装路径（B4A，三步内从基因组到可运行）：

1. `yiagent hof pull <gene_hash>` — 名人堂基因组落盘 `~/.yiagent/hof/`
2. `yiagent assemble <hof包> --variant <id>` — 校验 + 装配 + 落盘 vector JSON
3. `yiagent chat|run --vector <vector.json>` — `AgentSession(vector=...)` 直接
   消费装配产物：基因组文本与 Skill 盒从配置包复原，构造即发 `genome_pack` 事件

场景演示包（B4B）见 `demo/kepu/`：手工种子等位 → 样例 vector（固定时间戳，
`build_vector.py` 可逐字节复现）→ smoke/checklist 全 offline；live 对话演示
由人按 README 步骤触发。

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
