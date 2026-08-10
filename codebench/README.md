# YiAgent codebench（编程榜 · 档 B）

目标：`GOAL-CODEBENCH-B-001`（见 `工作台/编程榜目标.md`）

| 项 | MVP |
|----|-----|
| 模型 | 仅 Kimi |
| 题量 | LiveCodeBench `release_v5` **50 题抽样** |
| UI | console **榜单** 区 → 编程榜 |
| 判分 | Docker 沙箱执行，pass@1，无 LLM 裁判 |

## 起服务

```bash
cd YiAgent/codebench
docker compose up -d --build
curl http://127.0.0.1:8791/healthz
```

## M0 自测（容器内）

```bash
docker compose exec codebench python tests/test_executor.py
```

## API

- `GET /healthz`
- `GET /api/goal`
- `POST /api/exec` `{ "code", "tests", "language":"python" }`

## 里程碑

- **M0** 执行器（本目录）
- **M1** 50 题抽样 + Kimi 出分
- **M2** console 榜单区展示
