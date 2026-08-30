# 知识三平面 · DEC-039

| id | AIOS-GRAPH-C |
|----|--------------|
| status | refined |
| updated | 2026-08-30 |
| revision | 2 |
| owner_task | task-C |

> 文档平面 = 叙事 SoR；图谱平面 = 关系 SoR (P2)；RAG 平面 = 向量索引（非正文库）。可见性 `ai_ok` / `both` / `deny_ai`；Agent 仅挂载 `ai_ok`/`both`。

```mermaid
flowchart TB
  subgraph doc_plane["文档平面 · 叙事 SoR"]
    m5["M5 存档<br/>原始叙事源"]
    cert["认证切片<br/>合规/版本裁剪"]
    m4["M4 文档面<br/>可读叙事 SoR"]
    m5 --> cert --> m4
  end

  subgraph graph_plane["图谱平面 · 关系 SoR P2"]
    ent_hub["实体圈"]
    biz["业务线"]
    cust["客户"]
    proj["项目"]
    owner["负责人"]
    term["术语"]
    own_edge["归属边<br/>belongs_to / owns / defines"]
    ent_hub --- biz
    ent_hub --- cust
    ent_hub --- proj
    ent_hub --- owner
    ent_hub --- term
    biz --> own_edge
    cust --> own_edge
    proj --> own_edge
    owner --> own_edge
    term --> own_edge
  end

  subgraph rag_plane["RAG 平面 · 检索层"]
    vec["向量索引<br/>embedding 检索"]
    note_rag["非正文库<br/>不替代 M4/M5 叙事 SoR"]
    vec --- note_rag
  end

  subgraph vis["可见性 · visibility"]
    ai_ok["ai_ok<br/>Agent 可读"]
    both["both<br/>人+Agent 可读"]
    deny_ai["deny_ai<br/>Agent 禁读"]
  end

  subgraph mount["Agent 挂载策略"]
    mount_rule["仅挂载 ai_ok / both<br/>deny_ai 永不注入上下文"]
  end

  subgraph route["问句路由 · query routing"]
    q_rel["关系题<br/>谁负责/归属/关联"]
    q_nar["叙事题<br/>背景/过程/细节"]
    q_mix["混合题<br/>关系+叙事"]
    ans_graph["图谱优先<br/>实体圈 + 归属边"]
    ans_rag_doc["RAG + 文档面<br/>向量召回 + M4 叙事"]
    ans_hybrid["图定边界 + RAG 填细节<br/>图谱圈范围 → RAG 补叙事"]
    q_rel --> ans_graph
    q_nar --> ans_rag_doc
    q_mix --> ans_hybrid
  end

  m4 --> vec
  m4 -.->|"实体抽取 / 对齐"| ent_hub
  cert -.->|"可见性标注"| vis
  m4 -.->|"可见性标注"| vis
  ent_hub -.->|"可见性标注"| vis
  vec -.->|"可见性标注"| vis
  vis --> mount_rule
  mount_rule --> route

  ans_graph --> graph_plane
  ans_rag_doc --> rag_plane
  ans_rag_doc --> doc_plane
  ans_hybrid --> graph_plane
  ans_hybrid --> rag_plane
```

## 读图要点

- **三平面分工**：M5→认证切片→M4 承担叙事 SoR；实体圈+归属边承担关系 SoR (P2)；向量索引仅做检索，不替代正文库。
- **可见性三分**：`ai_ok`/`both`/`deny_ai` 标注于各平面产出；Agent 上下文只挂载 `ai_ok` 与 `both`，`deny_ai` 永不注入。
- **关系题走图谱**：问归属、负责人、业务线-客户-项目关联时，优先查实体圈与归属边，而非向量全文检索。
- **叙事题走 RAG+文档**：问背景、过程、细节时，以 M4 文档面为叙事锚点，向量索引做语义召回补充。
- **混合题分层**：先用图谱圈定实体边界与关系范围，再用 RAG 在边界内填充叙事细节，避免跨实体幻觉。

## Changelog

| revision | date | note |
|----------|------|------|
| 1 | — | 初稿占位（task-C） |
| 2 | 2026-08-30 | 细化三平面节点、可见性三分、Agent 挂载规则与问句路由（关系/叙事/混合） |
