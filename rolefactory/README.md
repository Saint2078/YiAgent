# 高性能角色工厂（rolefactory）

独立容器服务。输入一个角色名（例如「数据分析专家」），自动完成：

```
锚点检索 → 能力维度蓝图 → 题组 + 裁判 rubric → G1–G5 基因库
        → 基线（无基因 / 全弱基因）→ 多代进化选种 → holdout 鉴定 → 冠军基因组
```

分数全部实跑，没有冻结演示数据。演示版（结构展示、分数标未实跑）在 console 的「角色工厂」页；
本服务对应 console 的「角色工厂·实跑」页。

## 为什么单独一个容器

- 与 console / factory 解耦：全 async（httpx + uvloop），一次 run 内所有「作答→裁判」并行提交，
  由信号量统一限流，不受原 factory 线程池模型的限制。
- 资源可单独设限（compose 里 `cpus: 2.0` / `mem_limit: 1g`），压测和实跑不影响控制台。
- 状态与缓存落在自己的 `./data` 卷里，可整体删除重来。

## 高性能做法

| 手段 | 位置 | 作用 |
| --- | --- | --- |
| 全链路 async + 连接池（HTTP/2 keep-alive） | `app/llm.py` | 单进程即可撑住数十路在飞请求 |
| 信号量限流 + 指数退避抖动重试（含 `Retry-After`） | `app/llm.py` | 429/5xx 自愈，不放大雪崩 |
| 磁盘缓存（sha256(model+messages+params)） | `app/llm.py` | 精英变体跨代复评 ≈ 0 成本；重跑可复算 |
| `salt` 只进缓存键、不进请求体 | `app/llm.py` | 重复采样各自独立，同时保留重跑可缓存 |
| 维度级并行出题、代内全量并行评测 | `app/roles.py` / `app/pipeline.py` | 墙钟时间从串行的数十分钟压到数分钟量级 |
| token / 墙钟双预算护栏 + 早停 | `app/pipeline.py` | 花费可控，收益停滞即止 |
| temperature 自适应降级 | `app/llm.py` | k3 只接受 `temperature=1`，命中 400 后自动改为不传该参数 |
| 客观判分不过模型 | `app/objective.py` | 判分是纯 Python，省掉一次裁判调用，单条评测成本减半 |

## 起服务

```bash
cd A002.YiAgent/YiAgent/rolefactory
docker compose up -d --build
curl http://127.0.0.1:8790/healthz
```

Key 从 `../secrets/kimi.key` 以只读方式挂进 `/run/secrets/kimi.key`（该路径已被 `.gitignore` 排除）。
也可以用 `RF_API_KEY` 环境变量，或在请求体里传 `api_key`。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/healthz` | 模型、并发、Key 是否挂载、锚点索引是否可读 |
| GET | `/api/bench` | benchmark 策展索引（含 `runnable_here` / `blocked_by`） |
| GET | `/api/anchors?role=` | 某角色命中的锚点 |
| POST | `/api/perf/probe` | 并发压测：吞吐 / p50 / p90 / 并行加速比 |
| POST | `/api/run` | 启动全链路，返回 `run_id` |
| GET | `/api/run/{id}` | 实时快照（阶段、评测进度、tokens、吞吐、各代分数） |
| GET | `/api/run/{id}/report` | 最终报告（含冠军基因组、holdout、性能、caveats） |
| GET | `/api/run/{id}/results` | 逐条评测明细（`full=true` 带回答原文） |
| POST | `/api/run/{id}/shadow` | 对已存回答补跑 LLM 裁判，与客观分并列比区分度 |
| POST | `/api/run/{id}/abort` | 中止（预算/墙钟同样会自动中止） |
| GET | `/api/case/{role_id}` | 沉淀的题库（`data/case/role/<role_id>/testcases.jsonl`） |

启动参数（`POST /api/run`）：`role`（必填）、`scoring_mode`（`objective` 默认 / `judge`）、
`judge_shadow`、`per_dim`、`generations`、`variants_per_gen`、`reps`、`holdout_reps`、`elite`、
`min_gain`、`patience`、`concurrency`、`budget_tokens`、`budget_seconds`、`seed`。

两个参数值得单独说：

- `variants_per_gen` 建议 **10–12**（默认 6）。32 并发下 5 个变体只用掉约一波，闸门在闲着；
  受控对照里变体数 5→12 让同相位评测数翻倍而墙钟只多 10.6%（[PERF.md](PERF.md) §8）。
  代价是 token 随变体数线性涨。
- `holdout_reps` 默认 **3**（与 `reps` 分开）。holdout 只有 2 个臂 × 5–6 题，是全流程最便宜的
  一段，却是「有没有泛化」的唯一判据。
  **但别指望靠它判出结论**：方差分解（[PERF.md](PERF.md) §10.1）显示 6 题时半宽下限 1.72
  已大于实测效应 1.41 —— 重复多少次都判不了，只能加题（最省配法 `reps=1 × 55 题`）。
- `holdout_per_dim` 默认 **1**：每维度留几道给 holdout。**这是 holdout 题量的唯一开关** ——
  调 `per_dim` 只会把题都加到 train，holdout 恒等于维度数（约 6 道，见 §10.2）。
  想判定就 `{"per_dim": 10, "holdout_per_dim": 9, "holdout_reps": 1}`（train 6 / holdout 54）。

## 命令行工具

| 工具 | 用途 |
| --- | --- |
| `tools/genome_card.py <run_id>` | 生成基因组卡：内容哈希 / 逐槽消融 / 泛化判定 / 复现配方（json + md） |
| `tools/genome_card.py verify <run_id> <genome.json>` | 校验落盘基因组是否就是该次实跑的冠军 |
| `tools/perf_summary.py [run_id...]` | 性能画像：并发利用率、阶段耗时、purpose 级 token/秒 |
| `tools/build_devteam.py [席位...]` | 批量构建 Develop 六席并写登记表 |
| `tools/build_devteam.py adopt <席位> <run_id>` | 采纳一次已完成的 run 为该席位基因组，不重跑 |
| `tools/build_devteam.py registry` | 只按现有落盘基因组重写登记表 |
| `tools/export_yiagent_bank.py <run_id>\|--seat X\|--all` | 实跑冠军 → `yiagent` 能装配的基因库（带血统与泛化判定） |
| `tools/audit_checks.py` | 审计 `must_not_include` 误判率（把「引用反驳」误判成「说错话」的比例） |
| `tools/audit_cases.py [--by-run] [--raw]` | 历史题库对当前校验口径的通过率，估收紧校验要多烧多少出题调用 |
| `tools/gameability.py [--raw] [--target-numeric 0.6]` | 量化堆词假答案能拿多少分（`--raw` 看清洗归一前的地板） |
| `tools/check_contrib.py [run_id...]` | 把「冠军−基线」分差拆到每类断言，看谁在区分强弱、谁只是送分 |
| `tools/rescore.py [--write]` | 用当前打分口径离线重算历史实跑，看冠军/分差会不会变（不花额度） |
| `tools/power_check.py [--md]` | 判定力核算：现有题量能判出多大效应、判出实测效应要多少题（离线） |
| `tools/variance_decomp.py <run_id> [--source auto\|run\|reholdout]` | 方差分解：拆开题内噪声与题间差异（离线；需 reps≥2，会自动去 `<run>-reholdout/` 找） |
| `tools/decomp_table.py [--md]` | 六席处方表：每席该加重复 / 该加题 / 判不了，并给「不出新题只加重复」的配法（离线） |
| `tools/probe_reps.py` | 扫一遍哪些 run 存了逐次分数、能不能做分解（离线） |
| `tools/headroom.py [--min-gain 5]` | 基线可涨空间：多少题贴天花板量不出提升，以及 Δ 被截断偏了多少（离线） |
| `tools/case_outliers.py <run_id>` | 留一法：哪道题在撑着结论（**诊断用，不是筛题用**；离线） |
| `tools/show_case.py <run_id> <题号子串>` | 并排看一道题的断言 / 两臂回答 / 逐条得分（离线） |
| `tools/variance_by_check.py <run_id>` | 每题分差的方差摊在哪类断言上（离线） |
| `tools/dim_delta.py <run_id>` | 效应是否按维度异质，以及多少题分差恒为 0（离线） |
| `tools/numeric_spread.py` | numeric 的 60% 权重摊在几条断言上（离线） |
| `tools/recheck_plan.py` | 天花板题会不会把"只加重复就够"的处方算歪（离线） |
| `tools/run_reholdout.py <run_id> [--reps 3] [--seat PM] [--wait-quota]` | 单独重跑某 run 的 holdout（**要额度**），跑完打方差分解；给 `--seat` 就顺带传导到下游四处 |
| `tools/queue_decisive.py` | 等额度，按「最便宜的可判席位」顺序跑高重复复核（顺序由 `decomp_table` 算出） |
| `tools/holdout_table.py [--md]` | 六席 holdout 判定汇总（两个 Δ 分列 + 区间归属，有复核就用复核；离线） |
| `tools/quota_probe.py` | 一次请求探上游额度是否可用（用服务端密钥，退出码 0=可用） |
| `tools/watch_quota_reholdout.py [--pilot 席位]` | 额度封顶时等待；恢复即补齐 holdout 复核，可再跑一次**只跑不采纳**的 v3 试跑 |

## 从实跑冠军到可运行 Agent

实跑产出的是基因，不是能跑的东西。接上装配链路：

```bash
python tools/export_yiagent_bank.py --all             # 六席 → data/yiagent_banks/*.bank.json
python tools/export_yiagent_bank.py --seat PM         # 单席，落点同上
cd .. && python scripts/build_agent_entities.py --refresh   # → 载体 + offline 检验 + 登记表
python scripts/verify_chain.py                        # 五处产物对账（断链退出码 1）
```

**跑完复核就得把四处一起刷**（卡片 / 落盘基因组 / 席位基因库 / 载体）。少刷一处不会报错，
只有 `verify_chain.py` 会报 —— 实测过一次五席断链。守护脚本已把这几步串在一起。

导出的基因库里 `variant.hash` 就是基因组卡的规范哈希，所以载体的 `markers.gene_hash`
能回溯到这次实跑；`meta.provenance` 带着泛化判定与一条 `claim`（这份基因允许对外说什么）。
**未在 holdout 上证明更强的基因照样能装配**（判定问的是「比无基因强吗」，不是「能不能用」），
但载体会自带这句话；要卡死就用 `yiagent assemble --require-generalization`。

## 评分口径

默认 `scoring_mode=objective`：**判分不过模型**，每题自带可程序校验的断言，详见 [SCORING.md](SCORING.md)。
`scoring_mode=judge` 切回 LLM 裁判 rubric 模式（做对照实验用）。

- 题级分 = 重复采样均值；维度分 = 该维度题均值；`weighted` = 按蓝图维度权重加权。
- `composite = weighted − 0.5 × σ(题级分)`，选种用 composite，避免只赢在个别题上。
- `holdout` 不参与选种，用于看是否过拟合；报告里给 `generalization_gap` 与 paired 明细。

### 什么时候才算「这套基因更强」

`delta_train_weighted` **不是战绩** —— 它算在被用来选冠军的同一批题上，天然偏乐观。
判定只看 holdout 的配对差值，且必须过区间：

- `paired.mean_delta_ci95`：对题重采样 2000 次的自助 95% 区间，固定 seed 可复算。
- 区间整体在 0 以上 → 站得住；整体在 0 以下 → 未通过（train 增益是过拟合）；
  **跨 0 → 判「判不了」，不许当赢**。换一组题就可能翻符号。
- 判定写进基因组卡的 `verdict`，也写进落盘 `genome.json` 的 `source.verdict`，三处同口径。

**报告里有两个 holdout Δ，别混**：

| 字段 | 算法 | 区间 |
|---|---|---|
| `holdout.delta_weighted` | 先按维度权重压成总分，再两臂相减 | **无** |
| `holdout.paired.mean_delta` | 逐题相减再平均 | `mean_delta_ci95` **只属于它** |

两者能差几倍（实测 1.66 对 0.36）。把区间挂到加权 Δ 上写，读的人会以为它快显著了 ——
这正是区间纪律要防的事。凡两者同现处都分行标明算法（PERF.md §16.2）。

自测：`python -m tests.test_stats`（离线，守住「跨 0 不许判赢」与旧 run 的退化路径）。

## 实测（两次全链路）

| run | 角色 | 判分 | 基线 | 冠军 | holdout Δ | 结论 |
|-----|------|------|------|------|-----------|------|
| `20260808-175616-ec5bbf` | 数据分析专家 | LLM 裁判 | 86.42 | 93.81 | **−0.35** | 天花板效应，搜不动 |
| `20260808-183754-70aab5` | 产品分析专家 | 客观断言 | 85.20 | 92.80 | **+4.06** | 5 题 3 升 0 降，有泛化增益 |

换成客观判分后，单条评测成本从 9332 tokens 降到 4012（少一次裁判调用），且基因贡献可排序
（消融 G5 −9.4 / G4 −6.0 / G3 −4.4 / G2 −2.4 / G1 −2.8）。

## 已知限制（写进报告 caveats）

1. 题目与标准答案仍由 LLM 生成，已用 `computation` 重算自校，但保证不了业务口径设计得好。
2. `must_include` 的关键词匹配可被堆词部分蒙到；用 `numeric`（权重≥35）与 `must_not_include` 压制，
   不能完全排除。
3. benchmark 只作题型与判分口径锚点；DABstep / DABench 等原题实跑需数据文件与代码执行沙箱。
4. 样本量小（题数 × 重复数），分差要连同 `σ`、`paired`、`min_case` 一起读，不做显著性声明。
