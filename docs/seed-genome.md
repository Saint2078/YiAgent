# AI 科普串联助手 · 种子基因组与需求句模板（目标 A 收尾）

对应评测包：`项目调研/04-AI科普助手-评测包/`（00-规格一页 / 01-裁判与门禁 / 02-题库清单）。
本文覆盖 A1A（需求句→manifest 模板）、A2A（种子槽位评分锚点）、A2C（黑盒约束声明）、A3A（manifest 构成）。

---

## 1. 需求句 → manifest 字段映射模板（A1A）

把一句自然语言需求拆成四块，逐块映射到 `POST /api/testset/manifest`（`testset.build_manifest`）的字段：

| 需求句成分 | 问自己 | manifest 字段 | 取值口径 |
|------------|--------|---------------|----------|
| 场景（做什么） | 对应哪个套件/题型的产出？ | `suites` / `dimensions` / `q` | 选器越窄越好：单一套件避免混题型污染均分（冒烟教训） |
| 受众 + 成功样子 | 写进 demand 原文，供 report 与锚点题生成 | `demand` | 需求句原文，不删减 |
| 约束（级别/范围） | 题目可用性级别？ | `level` | 默认 `basic`；题目录 `levels` 含该级别才会入选 |
| 成功样子（样本量） | 进化集几题？终验几题？ | `size` / `holdout_ratio` / `seed` | holdout = `round(size × ratio)` 且受余题数封顶；须落 3–5 题；`seed` 固定保证可复现 |

### 填好的样例（本次科普需求）

需求句（规格一页原文）：
`我需要一个专门写 AI 技术与产品科普短文的 Agent，面向普通人，公众号可读，可联网查证。`

| 字段 | 值 | 理由 |
|------|----|----|
| `demand` | 需求句原文 | — |
| `suites` | `["科普短文"]` | 单一套件、单题型（`test_type=ai_科普`），规避混题型污染 |
| `level` | `basic` | 12 题 basic 全覆盖（仅 4 题另有 medium，不混级） |
| `size` | `8` | 题库仅 12 题；8 题进化集保住按题配对统计（n≥2 余量充足），余 4 题给 holdout |
| `holdout_ratio` | `0.5` | `round(8×0.5)=4`，落 3–5 区间。注意 02-题库清单示例的 `0.25` 只会得 `round(8×0.25)=2` 题，触发 preflight「<3 不可下结论」警告；0.5 是 12 题规模下唯一同时满足「进化集 ≥8、holdout ≥3」的档位（API 上限 0.5） |
| `seed` | `42` | 同 seed 同抽样，可复现 |

产出 manifest：**`factory/save/manifests/0803c197a73c.json`**

- 进化集 8 题：pop_bound_001/002、pop_chain_001/002、pop_article_001/002、pop_product_001、pop_verify_002（五维度标签全覆盖）
- holdout 4 题：pop_chain_003、pop_product_002、pop_article_003、pop_verify_001（串联/产品/短文/查证各 1）
- 离线核验：`load_manifest` 可加载；`resolve_cases` 展开 12 题 criteria 五维齐全、权重和 100；`run_preflight` 对该 manifest **无 errors、无混题型/跨套件 warning**（holdout 4 题仅有「<5 建议」级提示）。测试：`tests/test_ai_kepu_goal_a.py`。

---

## 2. 种子基因组（A2 / A2A）

落盘：**`factory/fixtures/seed/ai_kepu_seed.json`**（每槽 2–3 等位，2 个种子 variant）。

文件双形态（与 HOF `GET /api/hof/genome/{gene_hash}` 同构）：

- 顶层 `variant_id / slots / slot_texts` 与 factory `bank_from_improve_seed` 入参同构——**整个文件可直接作为 `POST /api/evolve/start` 的 `seed` 字段**（多余字段被忽略）；
- `bank` 为完整等位库（`alleles` + `variants`），供查阅与进化合并。

种子 variant：

| variant | 组合 | 定位 |
|---------|------|------|
| `var.kepu.seed_a` | curator × plain × public_facts × chain × reader_first | 白话串联主线 |
| `var.kepu.seed_b` | curator × plain × public_facts × verify_first × fact_habit | 查证先行主线 |

### 每槽评分锚点说明（A2A）

等位文本只写身份/语气/知识习惯/成文策略/经验动作，锚定五维裁判的**可打分差异**，但不引用裁判原文：

| 槽 | 种子等位 | 锚定维度 | 对照等位（不进种子 variant，用于拉开分差） |
|----|----------|----------|-------------------------------------------|
| G1 身份 | `g1.kepu.curator` 科普串联者 | 全局：身份决定「编辑型讲解」基调 | `g1.kepu.reporter` 科技记者（易滑向资讯罗列 → structure_chain 偏弱） |
| G2 语气/边界 | `g2.kepu.plain` 白话克制 | readability_wechat（少黑话）、no_hype（不煽动） | `g2.kepu.hype` 营销腔（no_hype/boundary 大丢分）；`g2.kepu.academic` 论文腔（readability 丢分） |
| G3 知识挂载 | `g3.kepu.public_facts` 公开事实可核对 | accuracy_verified（可核对/标未核实）、boundary_honesty | `g3.kepu.insider` 自称内部消息（触发一票否决风险）；`g3.kepu.glossary_only` 名词卡片（串联弱） |
| G4 能力规划 | `g4.kepu.chain` 串联成文 / `g4.kepu.verify_first` 查证先行 | structure_chain（主线+误区）、accuracy_verified（先核对再成文） | `g4.kepu.listicle` 词条罗列（structure_chain 弱） |
| G5 经验层 | `g5.kepu.reader_first` / `g5.kepu.fact_habit` | boundary_honesty（不给越权结论）、accuracy_verified（查证习惯） | `g5.kepu.sloppy` 凭印象写（accuracy/boundary 丢分） |

对照等位的用途：初始种群即存在可分辨的表型差，裁判五维能打出分差，进化第一轮就有选择压力。

## 3. 黑盒约束声明（A2C：告知 ≠ 提升）

- 本种子库是**初始群体**，不是进化成果。等位文本来自规格一页「能做/不做」的工程化转写，**未灌装任何题的 criteria / rubric 原文**（测试 `test_seed_alleles_no_rubric_leak` 断言等位文本不含五维 id、`weight`、`90-100` 分档字样）。
- 基因组质量的一切提升必须走 **变异（local/wide 精炼、交叉、随机移民）+ 鉴定（manifest 题集 × 裁判）+ 配对晋升门禁** 的闭环；禁止把规格文本或评分标准灌进等位冒充「进化结果」。
- 对照基线由流水线自带：arm A（无基因组）/ arm B（灌完整评分标准上界），种子不需要也不应该扮演基线。

---

## 4. 规格一页「能做/不做」核验（A1B / A5C）

结论：**可直接挂题目与裁判，无缺项**（未改动评测包任何文件）。

| 规格条目 | 挂载点 |
|----------|--------|
| 能做·知识整理串联（概念→关系→常见混淆） | pop_chain_001/002/003 三题 + `structure_chain` 维（w25） |
| 能做·公众号风格短文 | 全部 12 题题面均要求公众号短文 + `readability_wechat` 维（w25） |
| 能做·联网核对名词/产品定位/公开能力/时间线 | pop_verify_001/002 两题 + `accuracy_verified` 维（w25） |
| 能做·标明不确定与「该问谁」 | `boundary_honesty` 维（w15）+ pop_bound_002 自检清单要求 |
| 不做·投资/采购/医疗/法律结论 | pop_bound_001（荐股拒答）+ 硬门槛 #2 越权建议 + `boundary_honesty` 0–59 档 |
| 不做·论文墙/术语堆砌/营销软文 | `readability_wechat` / `no_hype`（w10）维 + 文体失控软门槛 |
| 不做·编造参数/伪造引用/假装内部消息 | 硬门槛 #1 编造查证 + pop_verify_002 传闻核查 + `accuracy_verified` 0–59 档 |
| 不做·贬损竞品/阴谋论/神化 AI | `no_hype` 维 + pop_product_001「非导购」+ pop_bound_002「AI 意识」纠错 |

观察项（非阻断）：「不做」中的医疗/法律结论无专门题目，仅由 `boundary_honesty` rubric 与硬门槛 #2 覆盖；投资类有 pop_bound_001 一题。若要题面级覆盖医疗/法律拒答，需评测包侧补题，不在本任务范围。
