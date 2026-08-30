# B · Runtime Path（主运行路径）

| 字段 | 值 |
|------|-----|
| id | AIOS-GRAPH-B |
| status | refined |
| updated | 2026-08-30 |
| revision | 2 |
| owner_task | task-B |

```mermaid
flowchart LR
    human_goal["人定目标"]
    team_queue["Team就绪队列"]
    agent_exec["Agent执行"]
    human_gate{"需人审 gate"}
    awaiting_human["awaiting_human"]
    approve["approve"]
    reject["reject"]
    takeover["takeover"]
    approval_jsonl["approval.jsonl"]
    m3_pep{"M3_PEP<br/>ALLOW / DENY"}
    write_sor["写 AIOS_SoR"]
    intercept["拦截"]
    m6_audit["M6_JSONL audit"]
    autopilot_note["Autopilot<br/>async note"]

    human_goal --> team_queue
    team_queue --> agent_exec
    agent_exec --> human_gate

    human_gate -->|免审 / 已批准| m3_pep
    human_gate -->|需人审| awaiting_human

    awaiting_human --> approve
    awaiting_human --> reject
    awaiting_human --> takeover

    approve --> approval_jsonl
    reject --> approval_jsonl
    takeover --> approval_jsonl

    approval_jsonl -->|reject| team_queue
    approval_jsonl -->|approve / takeover| m3_pep

    m3_pep -->|ALLOW| write_sor
    m3_pep -->|DENY| intercept

    write_sor --> m6_audit
    intercept --> m6_audit

    m3_pep -.->|DENY 回队| team_queue

    agent_exec -.->|trail 执行链路| m6_audit

    autopilot_note -.-> agent_exec
```

## 读图要点

- 主链路从左到右：人定目标 → Team 就绪队列 → Agent 执行 → M3_PEP 判定 → 写 SoR 或拦截 → M6 JSONL 审计；ALLOW 走写库，DENY 走拦截，二者均汇入 audit。
- **需人审 gate** 在 Agent 与 M3_PEP 之间：高风险或策略要求时进入 `awaiting_human`，否则直达 PEP。
- 人审三出口 `approve` / `reject` / `takeover` 均写入 **approval.jsonl**；reject 回到 Team 队列，approve/takeover 继续 PEP。
- **M3_PEP DENY** 除拦截与审计外，虚线回 **Team 就绪队列** 以便重排或换策略再执行。
- **trail 执行链路**（Agent → audit 虚线）与 **Autopilot async note** 标注异步旁路：执行轨迹与自动巡航备注并行落审计，不阻塞主 ALLOW 写 SoR 路径。

## Changelog

- **rev 2 · 2026-08-30 · task-B**：refined 主运行路径图（AIOS-GRAPH-B）；补全人审 gate（awaiting_human / approve / reject / takeover / approval.jsonl）、trail 执行链路、Autopilot async note、M3_PEP DENY 虚线回队。
- **rev 1 · 2026-08-30 · task-B**：初稿骨架：人定目标 → Team 队列 → Agent → M3_PEP → SoR/拦截 → M6 audit。
