# 组装测试工厂 · Factory Demo

YiAgent 开源仓内的**可点筛选台**（Docker only）。

> 用基因工程定义 Agent：变异、筛选，而不是调一句 prompt。

## 一键打开

```bash
cd factory
docker compose up --build
```

浏览器打开 [http://localhost:8787](http://localhost:8787)。

## 流水线（7 步）

1. **口述 + API Key + 模型** → 生成筛选题目与评分标准（可手改）
2. **题目 / 裁判核对** → 左侧原题（选手），右侧裁判标准（不进基因组）
3. **标准基线 A/B**（多线程并行）
   - **A**：原题 system + user（最低对照）
   - **B**：host + 完整评分标准灌进 system（理论上限 / 教考泄露）
   - 默认每组 5 次；可跳过
4. **生成 G1–G5 基因组**（等位基因 + 候选 variants，会话内存）
5. **初筛**：合格线默认 mean≥70；达到「合格个数」后早停
6. **冠军池**：合格默认入池，可勾选增删
7. **终筛** → 标记 **效果最优 / 稳定最优 / 均衡最优**

### 怎么读 A / B / 基因组（C）

| 条件 | 含义 |
|------|------|
| A | 无标准泄露的地板 |
| B | 泄露天花板（往往够高，与基因无关） |
| 基因组（≈C） | 不灌标准；应落在 A→B 之间，看相对 A 的增益与稳定性 |

## 演示与保存

- **载入批判思维题**：只载入原题（或已有冻结包），**不自动开跑**；你手动点 A/B → 基因组 → 初筛 → 终筛。
- **保存会话**：顶栏「保存会话」→ `save/{时间戳}_…_v1.0.json` + `save/logs/` 运行日志。
- **固化为演示**：同上，并覆盖写入 `fixtures/demo_pack.json`（下次无 Key 也可展示含 A/B 的冻结结果）。
- **入库快照**：正式实跑另存 `fixtures/runs/{时间戳}_…_v1.0.json`（+ `_log_…`），可进 Git；`save/` 仍本地-only。

## 运行日志（本地；上传未实装）

模块：`server/run_log.py`。记录：

- 题目 / 口述 / 裁判标准（judge）
- A/B 基线分数与汇总
- 基因组 C（候选 variants）
- 初筛 / 终筛分数、池子、三标

落盘：`save/logs/{时间戳}_…json`（及 `.jsonl`）。  
远端发送：`SHIP_ENABLED=False`，`ship_to_server()` 仅占位，**当前不发网络**。

文案隐藏编辑：`Ctrl/⌘+Shift+E`，或 `?copyEdit=1`。

## 布局

```
factory/
  server/     # FastAPI：会话流水线 + Kimi + 裁判 + run_log
  www/        # 静态 UI
  fixtures/   # 演示题 / 等位基因库 / demo_pack.json
  save/       # 会话包 + logs/（gitignore）
  Dockerfile
  compose.yml
```

Key **不要**提交进 git；`factory/save/` 已在根 `.gitignore`。
