# 组装测试工厂 · Factory Demo

YiAgent 开源仓内的**可点筛选台**（Docker）。

> 别人调 prompt；我们改基因组，并用分槽鉴定决定晋升。

## 一键打开

在仓库根目录：

```bash
cd factory
docker compose up --build
```

浏览器打开 [http://localhost:8787](http://localhost:8787)。

## 流水线

1. **口述 + API Key + 模型** → 生成筛选题目与评分标准（可手改）
2. **生成 G1–G5 基因组**（等位基因 + 候选 variants，会话内存）
3. **初筛**：合格线默认 mean≥70；达到「合格个数」后早停；参数含初筛次数（默认 3）
4. **冠军池**：合格默认入池，可勾选增删
5. **终筛**：次数可设（默认 5）→ 标记 **效果最优 / 稳定最优 / 均衡最优**

旁路：**载入演示包**可灌入批判思维 fixture；真测需 Kimi Coding Plan Key（只存浏览器会话）。

## 布局

```
factory/
  server/     # FastAPI：会话流水线 + Kimi 调用 + 裁判
  www/        # 静态 UI
  fixtures/   # 演示题 / 等位基因库
  Dockerfile
  compose.yml
```

Key **不要**提交进 git；见仓库根 `.gitignore`。
