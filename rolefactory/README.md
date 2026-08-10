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
`judge_shadow`、`per_dim`、`generations`、`variants_per_gen`、`reps`、`elite`、`min_gain`、
`patience`、`concurrency`、`budget_tokens`、`budget_seconds`、`seed`。

## 评分口径

默认 `scoring_mode=objective`：**判分不过模型**，每题自带可程序校验的断言，详见 [SCORING.md](SCORING.md)。
`scoring_mode=judge` 切回 LLM 裁判 rubric 模式（做对照实验用）。

- 题级分 = 重复采样均值；维度分 = 该维度题均值；`weighted` = 按蓝图维度权重加权。
- `composite = weighted − 0.5 × σ(题级分)`，选种用 composite，避免只赢在个别题上。
- `holdout` 不参与选种，用于看是否过拟合；报告里给 `generalization_gap` 与 paired 明细。

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
