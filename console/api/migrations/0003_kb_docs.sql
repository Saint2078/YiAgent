-- Agent 知识库正文库（Markdown → SQLite，供编辑台可视化管理）

CREATE TABLE IF NOT EXISTS kb_doc (
  doc_id       TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  slug         TEXT,
  category     TEXT NOT NULL DEFAULT 'general',
  layer        TEXT,
  visibility   TEXT NOT NULL DEFAULT 'human_only'
               CHECK (visibility IN ('human_only', 'ai_ok', 'both', 'deny_ai', 'agent_api')),
  body_md      TEXT NOT NULL DEFAULT '',
  agent_slice  TEXT,
  source_path  TEXT,
  version      TEXT NOT NULL DEFAULT 'v0',
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_kb_doc_category ON kb_doc(category);
CREATE INDEX IF NOT EXISTS idx_kb_doc_visibility ON kb_doc(visibility);
CREATE INDEX IF NOT EXISTS idx_kb_doc_updated ON kb_doc(updated_at);
