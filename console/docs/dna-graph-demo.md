# DNA 图谱 · 最终表达集

状态：可用（2026-08-06）  
入口：`http://127.0.0.1:8188/dna-graph.html?genome=ai_architect`  
数据：`console/genome-packs.js`

## 约定

- **只展示最终表达基因**（全部纳入基因组）；界面无「对照 / 备选 / 反模式」。
- 标签统一为「基因」；详情为「最终表达基因 / 已纳入基因组」。
- 展示用，不要求实跑。

## 基因组

| id | 短名 | 规模（约） |
|----|------|------------|
| `ai_architect` | Architect DNA（默认） | ~56 |
| `product_manager` | 产品经理 | ~54 |
| `project_manager` | 项目经理 | ~54 |
| `evals_specialist` | Evals专员 | ~54 |
| `develop` | Develop | ~54 |
| `devops` | DevOps | ~54 |

## AI 架构师表达摘要

| 槽 | 基因主题 |
|----|----------|
| G1 | 软件架构师 · 多 Agent 系统设计 · 确定性软件为主 · 编排边界 |
| G2 | 权衡显式 · 生产门槛 · 最小权限 · 域先于技术 · 手术式范围 |
| G3 | ADR WHY · 12-Factor · Parnas · Seam · 分阶段演进 · 平台无关编排 |
| G4 | 结构化工具 · 门控工具 · 权限三态 · 统一遥测 · 方案≤3 |
| G5 | 规格门禁 · 契约优先 · Expand–Contract · 可观测问题 · 自有控制流 · 小 Agent · PR 架构审查 |
