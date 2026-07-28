# 组装测试工厂 · Factory Demo

YiAgent 开源仓内的**可点筛选台**（Docker only）。

> 用基因工程定义 Agent：变异、筛选，而不是调一句 prompt。

## 30 秒打开

```bash
cd factory
docker compose up --build
```

浏览器 → [http://localhost:8787](http://localhost:8787) → **载入冻结演示**  
（批判思维 · 含 A/B + 终筛，不调模型。）

## 流水线（7 步）

1. **口述 + API Key + 模型** → 生成筛选题目与评分标准（可手改）；**或从 `case/xsct` 用例库载入现成题**（无需 Key）
2. **题目 / 裁判核对** → 左侧原题（选手），右侧裁判标准（不进基因组）
3. **标准基线 A/B**（多线程并行）
   - **A**：原题 system + user（地板）
   - **B**：host + 完整评分标准灌进 system（天花板 / 教考泄露）
4. **生成 G1–G5 基因组**（等位基因 + 候选 variants）
5. **初筛**：合格线默认 mean≥70；凑齐合格数可早停
6. **冠军池**：合格默认入池，可勾选
7. **终筛** → **效果最优 / 稳定最优 / 均衡最优**

### 全自动（无人值守）

一步串起 1→7：`POST /api/session/auto`，或 UI「**全自动跑出最优基因**」。

- 用例库：body 含 `source=library` + `suite` + `id` + `level` + `api_key`
- 口述：`source=oral` + `oral` + `api_key`
- 默认取终筛 **均衡最优（balanced）**；结果写入 `save/*_best_genome_*.json` + 会话包
- 进度：轮询 `GET /api/session/{id}` 看 `auto_step` / `phase` / `best_genome`

### 怎么读 A / B / C

| 条件 | 含义 |
|------|------|
| A | 无标准泄露的地板 |
| B | 泄露天花板（往往够高，与基因无关） |
| 基因组（≈C） | 不灌标准；看相对 A 的增益与稳定性 |

当前冻结包（批判思维 · Kimi 3）：**A ≈ 68 · B ≈ 95 · 冠军 C ≈ 94**（更稳）。图见根 README。

## 演示 · 实跑 · 保存

| 动作 | 效果 |
|------|------|
| **载入冻结演示** | 读 `fixtures/demo_pack.json`，不调模型 |
| **实跑** | 「生成题目」或点「开始 A/B 基线」→ 基因组 → 初筛 → 终筛 |
| **保存会话** | `save/{时间戳}_…_v1.0.json` + `save/logs/` |
| **固化为演示** | 同上，并覆盖 `fixtures/demo_pack.json` |

入库快照：`fixtures/runs/`（可进 Git）；`save/` 本地-only（gitignore）。

## 运行日志

`server/run_log.py` 记录：题目 / 裁判 / A·B / 基因组 C / 初筛·终筛 / **token_usage**。  
远端上传：`SHIP_ENABLED=False`（占位，当前不发网络）。

每次 LLM 调用累计进会话 `token_meter`（输入 / 输出 / 合计 / 按 purpose）；快照与 `save/` 包内含 `token_usage`。

文案隐藏编辑：`Ctrl/⌘+Shift+E`，或 `?copyEdit=1`。

## 布局

```
factory/
  server/     # FastAPI + 薄封装（LLM 实现在 src/yiagent/providers）
  www/        # 静态 UI
  fixtures/   # 题 / 等位基因 / demo_pack.json / runs/
  save/       # 本地会话包（gitignore）
```

共享 Provider：`pip install -e .` 后 `from yiagent.providers import chat_completions, stream_chat`。

## 支持的模型（API）

| 厂商 | 模型示例 | Key |
|------|----------|-----|
| Kimi Coding Plan | `k3` · `kimi-k2.6` | Coding Plan Key |
| Moonshot | `moonshot-v1-auto` 等 | Moonshot Key |
| OpenAI | `gpt-4o` · `gpt-4.1` · `o4-mini` | `sk-…` |
| DeepSeek | `deepseek-chat` · `deepseek-reasoner` | DeepSeek Key |
| 通义 DashScope | `qwen-plus` · `qwen-max` | DashScope `sk-…` |
| 智谱 | `glm-4-plus` · `glm-4-flash` | 智谱 Key |
| Anthropic | `claude-sonnet-4-5` 等 | `sk-ant-…` |
| OpenRouter | Claude / Gemini 等 | `sk-or-…` |

界面按厂商分组；换模型会切换 Key 提示。Key **不要**提交进 git。
