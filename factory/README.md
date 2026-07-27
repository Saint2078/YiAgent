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

旁路：**载入演示包**（批判思维 fixture，跳过基线）；真测需 Kimi Coding Plan Key（只存浏览器会话）。

### 怎么读 A / B / 基因组

| 条件 | 含义 |
|------|------|
| A | 无标准泄露的地板 |
| B | 泄露天花板（往往够高，与基因无关） |
| 基因组（≈C） | 不灌标准；应落在 A→B 之间，看相对 A 的增益与稳定性 |

文案隐藏编辑：`Ctrl/⌘+Shift+E`，或 `?copyEdit=1`。

## 布局

```
factory/
  server/     # FastAPI：会话流水线 + Kimi + 裁判
  www/        # 静态 UI
  fixtures/   # 演示题 / 等位基因库
  Dockerfile
  compose.yml
```

Key **不要**提交进 git；`factory/save/` 已在根 `.gitignore`。
