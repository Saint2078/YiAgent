-- 项目状态增加 archived（归档，不物理删除）
PRAGMA foreign_keys=OFF;

CREATE TABLE project_new (
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

INSERT INTO project_new(
  project_id, title, category, owner, status, team, progress,
  due_text, risk, customer, pillar, channel, created_at, updated_at
)
SELECT
  project_id, title, category, owner, status, team, progress,
  due_text, risk, customer, pillar, channel, created_at, updated_at
FROM project;

DROP TABLE project;
ALTER TABLE project_new RENAME TO project;

PRAGMA foreign_keys=ON;
