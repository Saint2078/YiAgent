# AIOS Thin CRM · 实体关系图 (D)

| 字段 | 值 |
|------|-----|
| id | AIOS-GRAPH-D |
| status | refined |
| updated | 2026-08-30 |
| revision | 2 |
| owner_task | task-D |

## 概述

AIOS 薄 CRM 核心实体与关系：客户 → 商机 → 合同 → 发票 → 回款；负责人挂载于客户/商机/项目；客户归属业务线；项目回指客户；术语表为可选词汇表。

```mermaid
erDiagram
    CUSTOMER["客户 CUSTOMER"] {
        string customer_id PK
        string name
        string status
        string business_line_id FK
        string owner_id FK
    }

    OPPORTUNITY["商机 OPPORTUNITY"] {
        string opportunity_id PK
        string customer_id FK
        string owner_id FK
        string stage
        decimal amount
    }

    CONTRACT["合同 CONTRACT"] {
        string contract_id PK
        string opportunity_id FK
        string customer_id FK
        date signed_at
        decimal total_amount
    }

    INVOICE["发票 INVOICE"] {
        string invoice_id PK
        string contract_id FK
        string customer_id FK
        date issued_at
        decimal amount
        string status
    }

    PAYMENT["回款 PAYMENT"] {
        string payment_id PK
        string invoice_id FK
        date paid_at
        decimal amount
        string method
    }

    OWNER["负责人 OWNER"] {
        string owner_id PK
        string name
        string role
        string team
    }

    BUSINESS_LINE["业务线 BUSINESS_LINE"] {
        string business_line_id PK
        string name
        string code
    }

    PROJECT["项目 PROJECT"] {
        string project_id PK
        string customer_id FK
        string owner_id FK
        string name
        string status
    }

    TERM["术语 TERM"] {
        string term_id PK
        string key
        string definition_zh
        string domain
        string entity_ref
    }

    CUSTOMER ||--o{ OPPORTUNITY : "产生商机"
    OPPORTUNITY ||--o| CONTRACT : "赢单转化"
    CONTRACT ||--o{ INVOICE : "开票"
    INVOICE ||--o{ PAYMENT : "回款"

    OWNER ||--o{ CUSTOMER : "负责客户"
    OWNER ||--o{ OPPORTUNITY : "负责商机"
    OWNER ||--o{ PROJECT : "负责项目"

    BUSINESS_LINE ||--o{ CUSTOMER : "归属业务线"
    CUSTOMER ||--o{ PROJECT : "关联项目"

    TERM }o--o| CUSTOMER : "可选词汇"
    TERM }o--o| OPPORTUNITY : "可选词汇"
    TERM }o--o| CONTRACT : "可选词汇"
```

## 读图要点

- **主链路**：`CUSTOMER → OPPORTUNITY → CONTRACT → INVOICE → PAYMENT` 覆盖从潜客到现金的完整销售闭环，各节点以 FK 串联，便于 OPC 流程编排与状态追踪。
- **负责人 OWNER**：一对多挂载于客户、商机、项目三类对象，不直接绑定合同/发票/回款，体现「售前+交付」职责分离。
- **业务线 BUSINESS_LINE**：客户通过 `business_line_id` 归属单一业务线，支持多 BU 报表与权限隔离。
- **项目 PROJECT**：独立于商机链路，通过 `customer_id` 回指客户，用于交付/实施阶段与 CRM 主链并行存在。
- **术语 TERM**：可选词汇表，通过 `entity_ref` 软关联各实体，不参与交易约束，供 AIOS 语义层与 Agent 提示词对齐。

## Changelog

| revision | date | change |
|----------|------|--------|
| 1 | 2026-08-30 | 初稿：9 实体 + 主链/负责人/业务线/项目/术语关系 |
| 2 | 2026-08-30 | refined：补全属性字段、中文标签、术语软关联三端、读图要点 |
