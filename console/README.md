# 铱石 OPC · CEO 工作台

| 项 | 值 |
|----|-----|
| 定位 | **客户向产品面**（CEO 管组织 / 聊天 / 知识 / 项目 / 战略 / 审批 / 日程 / 待办） |
| 项目 SoR | **真落库**：`projects-api` → 桌面 `opc-demo/运行数据/projects/opc.sqlite` |
| Agent 运行时 | **DEC-044**：Compose `agent-bridge` · 容器内 SDK/API · 挂载 **桌面 `opc-demo/` → `/workbench`** |
| Cursor 工作台 | 消息频道 → `/api/agent/send`（实 SDK；豁免见 DEC-024/044） |
| 仍为 UI 模拟 | 其它 Team 消息 / 审批拍板 / 知识库 / 日程；待办为本机 localStorage |
| 部署 | `docker compose up -d --build` → http://127.0.0.1:8088/ |

## 持久化（Demo 默认桌面 `opc-demo/`）

与正式 `opc/` 分离；由 `.env` 的 `WORKBENCH_HOST_PATH` 指定。

| 宿主机路径 | 说明 |
|------------|------|
| `/Users/caelum/Desktop/opc-demo/` | Agent 工作目录（整树挂 `/workbench`） |
| `…/opc-demo/项目/<标题>/` | **每项目一文件夹**（新建时 API 自动建） |
| `…/opc-demo/运行数据/projects/opc.sqlite` | 项目库 |
| `…/opc-demo/运行数据/agent-bridge/.env` | Cursor / Provider 密钥 |
| `…/opc-demo/运行数据/agent-bridge/providers.json` | Provider 状态 |
| `…/opc-demo/公司资产/IT资产/` | SSH / API Key 正本 |

浏览器 `localStorage`（待办、资产缓存等）仍在本机浏览器，不进 `opc-demo/`。

## 产品菜单

| 项 | 说明 |
|----|------|
| 今日 | 今日日程 · 待办 · 审批摘要与快捷入口 |
| 日程 | 本周日条 · 会议/拜访/里程碑样例 |
| 待办 | 勾选 / 新建 / 删除 · **浏览器 localStorage** |
| 消息 | Team / 数字员工 · **Cursor 工作台（真 SDK）** |
| 资产 | 公司主机 / 云服务器 · 一键 SSH · 含阿里云 H1 |
| 设置 | Provider（供应商 Key / 模型）· 经 bridge 存 `opc-demo/运行数据/agent-bridge` |
| 审批 | 拍板 + 人审材料包（UI） |
| 项目 | **战略/客户** · 看板 · 详情 · **可编辑**（API → SQLite） |
| 战略 | 对齐 [05-战略](../../../05-战略/README.md) |
| 组织 | Team 与席位 |
| DNA | 公司 Develop 基因组 · G1–G5 · 审查委入口（UI；正本在 `opc-demo/AgentTeam/Develop`） |
| 知识库 | 人看 / Agent 看（内存样例） |
| 客户 | 轻量管道 |

## 启动

```bash
cd engineering/v1/demo-ceo-console

# 确认桌面 opc-demo 与运行数据文件存在（首次可从本 README「持久化」表核对）
# compose 读取本目录 .env → WORKBENCH_HOST_PATH=/Users/caelum/Desktop/opc-demo

docker compose up -d --build
```

打开 http://127.0.0.1:8088/。

| 服务 | 说明 |
|------|------|
| `ceo-console` | nginx · `/api/projects*` → projects-api · `/api/agent/` → **agent-bridge** |
| `projects-api` | Python · SQLite → `opc-demo/运行数据/projects` |
| `agent-bridge` | Node · `/workbench` = 桌面 opc-demo · 密钥 = `opc-demo/运行数据/agent-bridge` |

| 变量 | 说明 |
|------|------|
| `WORKBENCH_HOST_PATH` | 默认 `/Users/caelum/Desktop/opc-demo` |

冒烟：

```bash
curl -s http://127.0.0.1:8091/healthz
curl -s http://127.0.0.1:8088/api/projects
```

## 边界

- 决策：[DEC-044](../../../99-决策留档/DEC-044-Agent运行时-Docker挂载本机文件夹.md)
- SDK/API 只在容器内跑；持久化只认桌面 `opc/`
- `cursor-bridge/start.sh` 仅应急；主路径 Compose
