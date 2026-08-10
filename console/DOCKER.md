# YiAgent Console · Docker only

禁止在本机裸跑 `python -m http.server` / `npx serve` / 直跑 uvicorn。

## 仅 console（优化闭环 / 可调用实体 / DNA / 单题 UI 壳）

```bash
cd console
docker compose -f docker-compose.console.yml build
docker compose -f docker-compose.console.yml up -d
```

镜像使用 `Dockerfile.console`（静态 nginx，**无** factory/bridge upstream）。

打开 http://127.0.0.1:8188/

| 菜单 | US |
|------|-----|
| **DNA 全链路**（首页） | ROOT / 导览 |
| 单基因工作台 | US-001 |
| 基因组工作台 | US-003 |
| **优化闭环** | **US-002** |
| **可调用实体** | **US-004** |

工作台 Ship 清单：`A002.YiAgent/工作台/SHIP.md`

## 全栈（含 factory API）

```bash
cd console
copy .env.example .env
# 确保 _workbench/ 目录结构存在（见下）
docker compose build
docker compose up -d
```

`WORKBENCH_HOST_PATH` 默认 `./_workbench`。
