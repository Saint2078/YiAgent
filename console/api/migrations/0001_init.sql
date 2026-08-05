-- 01-storage 0001：M8 进度三表 + 知识浅层元数据（非正文库）
-- 审计仍走 JSONL；不做 Wiki 修订深表

CREATE TABLE IF NOT EXISTS project (
  project_id   TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  category     TEXT NOT NULL DEFAULT '战略'
               CHECK (category IN ('战略', '客户')),
  owner        TEXT,
  status       TEXT NOT NULL DEFAULT 'active'
               CHECK (status IN ('active', 'paused', 'done', 'cancelled', 'archived')),
  team         TEXT,
  progress     INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  due_text     TEXT,
  risk         TEXT,
  customer     TEXT,
  pillar       TEXT,
  channel      TEXT,
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS task (
  task_id              TEXT PRIMARY KEY,
  project_id           TEXT NOT NULL REFERENCES project(project_id) ON DELETE CASCADE,
  goal                 TEXT NOT NULL,
  assignee             TEXT,
  status               TEXT NOT NULL DEFAULT 'ready',
  needs_human_review   INTEGER NOT NULL DEFAULT 0 CHECK (needs_human_review IN (0, 1)),
  task_class           TEXT NOT NULL DEFAULT 'standard'
                       CHECK (task_class IN ('standard', 'long_running')),
  audit_trail_id       TEXT,
  due_text             TEXT,
  created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_task_project ON task(project_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON task(status);

CREATE TABLE IF NOT EXISTS blocker (
  blocker_id   TEXT PRIMARY KEY,
  task_id      TEXT NOT NULL REFERENCES task(task_id) ON DELETE CASCADE,
  kind         TEXT NOT NULL DEFAULT 'other',
  summary      TEXT NOT NULL,
  raised_by    TEXT,
  raised_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  cleared_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_blocker_task ON blocker(task_id);
CREATE INDEX IF NOT EXISTS idx_blocker_open ON blocker(task_id) WHERE cleared_at IS NULL;

-- 浅层知识元数据：正文在文件树 / data/files；此处只挂 visibility 与 locator
CREATE TABLE IF NOT EXISTS doc_meta (
  doc_id       TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  locator      TEXT NOT NULL,
  visibility   TEXT NOT NULL DEFAULT 'human_only'
               CHECK (visibility IN ('human_only', 'ai_ok', 'both', 'deny_ai', 'agent_api')),
  version      TEXT NOT NULL DEFAULT 'v0',
  folder       TEXT,
  updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_doc_visibility ON doc_meta(visibility);
