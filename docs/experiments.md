# Experiments · 批判思维演示口径

公开 README 数字一律来自 factory 冻结包，**只讲这一题**。

| 项 | 值 |
|----|-----|
| 包 | [`factory/fixtures/demo_pack.json`](../factory/fixtures/demo_pack.json) |
| 题 | `l_criticalthinking_059` 工作与休息二选一 |
| 模型 | Kimi 3（`k3`） |
| A | 原题对照 · n=5 · `[67.6, 67.9, 66.8, 70.6, 67.9]` |
| B | 灌入完整评分标准 · n=5 · `[96.0, 94.6, 95.2, 94.6, 93.7]` |
| C | 终筛冠军 `var.balanced_philosopher` · n=5 · `[93.9, 94.4, 93.7, 93.8, 93.7]` |

图：[`assets/demo_ct_abc_trials.svg`](assets/demo_ct_abc_trials.svg)（3 条实线试次 + 6 条虚线 mean±sd）  
再生：`python3 scripts/gen_factory_demo_charts.py`（读 demo_pack，stdlib SVG）。

---

# 实跑 playbook（题库就绪后的完整操作）

前提：factory 服务在 `:8787`（`docker compose -f factory/compose.yml up -d`），
Cursor 线交付的题库 manifest 已落盘（`factory/save/manifests/<manifest_id>.json`）。
key 三选一：请求体 `api_key` / 环境变量 `KIMI_API_KEY` / `secrets/kimi_coding_plan.key`。

## 1. 起飞前检查（必跑，不发 LLM、不读密钥内容）

```
curl -s 'http://localhost:8787/api/evolve/preflight?manifest_id=<manifest_id>' | python3 -m json.tool
```

- `ok:false`（errors 非空）→ 先修：manifest 缺失/损坏、无 API key 是仅有的硬失败。
- warnings 逐条过目：holdout<5、混题型（按 T1 分层口径解读）、HOF 未开启、无预算护栏等。

## 2. 正式跑（建议参数：holdout 3–5 题、eval_reps≥2、HOF 开启）

```
YIAGENT_HOF_ENABLED=1 docker compose -f factory/compose.yml up -d   # 如需上报先带 env 重启

curl -s -X POST http://localhost:8787/api/evolve/start \
  -H 'Content-Type: application/json' \
  -d '{
    "api_key": "<key>",
    "model": "k3",
    "manifest_id": "<manifest_id>",
    "max_generations": 4,
    "variants_per_gen": 6,
    "eval_reps": 2,
    "final_reps": 3,
    "max_tokens_budget": 2000000,
    "with_baseline": true
  }'
```

响应里附带 `preflight`（含 warnings）。**阻断口径选择：保守默认只警告不阻断**——
preflight 的 errors 不拦启动，因为 manifest 缺失/无 key 这两类硬失败在
`/api/evolve/start` 自身就会先抛 404/400；warnings 只提示，由人判断是否继续。

## 3. 看进度与报告

```
curl -s http://localhost:8787/api/evolve/<run_id>            # status/phase/done/total
curl -s http://localhost:8787/api/evolve/<run_id>/report     # 完成后取 report.json
```

report 落盘：`factory/save/evolve/<run_id>/report.json` + `report.md`。

## 4. 归档（跑完即归，本机可跑、不依赖 Docker）

```
python3 experiments/archive_evolve_run.py <run_id>
```

产出 `experiments/<YYYYMMDD>_<run_id>/`：`report.json` + `report.md` + `README.md`
（README 记录复跑口径：preflight/启动 curl、env、manifest id、原 run 参数）。

## 5. 预期产出清单（C1 度量回答口径）

- **墙钟分项**：`report.wall_by_stage`（每阶段秒数 + 占总墙钟百分比）与
  `report.wall_total_sec`；report.md「耗时分布」表。评测/变异（refine）/holdout/
  baseline 各占多少秒直接可查（裁判与答题同在 gen{N}_eval 阶段内，token 口径另见
  `token_usage.by_purpose`）。
- **token 分项**：`report.token_by_stage`（每阶段 calls/输入/缓存命中/输出/成本估计）。
- **门禁**：`report.gates[]` 的 `paired`（配对 t 检验 p 值 + bootstrap CI）与 verdict。
- **失败率**：`report.failure_rates`（全局 + 逐变体，>50% 标 unreliable）。
- **分层均分**：`report.champion_stratified`（混题型 manifest 必须按此逐层解读）。
- **A/C 对照**：`report.baseline_arm_a` 与 `report.champion_minus_baseline_mean`。
- **终验**：`report.holdout`（holdout n≥3 才可下结论，n=2 是冒烟教训）。
