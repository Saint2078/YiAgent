# YiAgent 名人堂（Hall of Fame）服务

社区基因组评分档案：opt-in 接收各地 factory 上报的评分卡，聚合出排行榜 / 等位边际表现 / 冠军基因组 seed 下载。
契约见 `../docs/20260731_名人堂服务规划.md`（payload schema 第三节、防刷第五节）。

## 运行

```bash
docker compose up -d hof        # 根 compose.yml，端口 8788
```

- 数据落 SQLite：容器内 `/app/data/hof.db`（`HOF_DB_PATH` 可覆盖），compose 挂 `hof_data` 卷持久化。
- 本地直跑：`pip install -r server/requirements.txt && uvicorn app:app --port 8788`（`server/` 目录下，默认库文件 `hof/data/hof.db`）。

## API

| 路由 | 说明 |
|---|---|
| `POST /api/hof/submit` | 批量 `{"submissions": [...]}` 或单份直接 POST；逐份返回接收/拒绝原因；整批被限流返回 429 |
| `GET /api/hof/leaderboard?dimension=&model=&suite=&min_n=3&limit=50` | 按 shrunk composite 排序 |
| `GET /api/hof/genome/{gene_hash}` | 完整 bank+variant + slots/slot_texts，可直接作 factory `evolve/start` 的 seed |
| `GET /api/hof/alleles?slot=G5&limit=50` | 等位边际表现（PBIL 分布导出） |
| `GET /api/hof/stats` | 总提交/基因组/贡献者/模型分布 |
| `GET /api/hof/submissions?limit=50` | 最近提交流水（含拒绝原因） |
| `GET /api/health` | 健康检查 |
| `GET /` | 可视化工作台（静态页，`www/`） |

## 结构

- `server/app.py` — 路由 + schema 校验 + 白名单 + rubric 反作弊 + 内存限流（30 份/分钟/贡献者）
- `server/store.py` — SQLite 三表（submissions / genomes / allele_stats）
- `server/aggregate.py` — 加权合并 + 贝塔收缩纯函数（m=5, prior=75）
- `www/` — vanilla JS 工作台：排行榜 / 等位表现 / 提交流水 / 概览
