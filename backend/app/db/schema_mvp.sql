-- finance-shared-agent-platform · SCHEMA_VERSION = 1
-- Source of truth (design): 03_数据库设计_MVP.md
-- Copied from design dir: 方案与文档/软件工程文档/2_设计/schema_mvp.sql
-- SQLite 3 · enable foreign_keys + WAL in application bootstrap

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id                    TEXT PRIMARY KEY,
  username              TEXT NOT NULL UNIQUE,
  display_name          TEXT NOT NULL,
  password_hash         TEXT NOT NULL,
  role                  TEXT NOT NULL CHECK (role IN ('user', 'admin')),
  status                TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
  must_change_password  INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
  last_login_at         TEXT,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL,
  deleted_at            TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_status_role ON users(status, role);

CREATE TABLE IF NOT EXISTS auth_sessions (
  id            TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash    TEXT NOT NULL UNIQUE,
  created_at    TEXT NOT NULL,
  expires_at    TEXT NOT NULL,
  last_seen_at  TEXT,
  revoked_at    TEXT,
  revoke_reason TEXT,
  ip            TEXT,
  user_agent    TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id, revoked_at);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS system_settings (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  updated_by  TEXT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS skills (
  id                 TEXT PRIMARY KEY,
  skill_key          TEXT NOT NULL UNIQUE,
  owner_user_id      TEXT NOT NULL REFERENCES users(id),
  visibility         TEXT NOT NULL CHECK (visibility IN ('private', 'pending', 'published', 'disabled')),
  title              TEXT NOT NULL,
  summary            TEXT NOT NULL DEFAULT '',
  risk_level         TEXT NOT NULL DEFAULT 'low'
                       CHECK (risk_level IN ('low', 'medium', 'high')),
  current_version    TEXT NOT NULL DEFAULT '0.0.0',
  content_hash       TEXT NOT NULL DEFAULT '',
  storage_kind       TEXT NOT NULL CHECK (storage_kind IN ('private_fs', 'published_git')),
  rel_path           TEXT NOT NULL,
  catalog_extra_json TEXT,
  created_at         TEXT NOT NULL,
  updated_at         TEXT NOT NULL,
  deleted_at         TEXT
);

CREATE INDEX IF NOT EXISTS idx_skills_visibility ON skills(visibility);
CREATE INDEX IF NOT EXISTS idx_skills_owner ON skills(owner_user_id);

CREATE TABLE IF NOT EXISTS skill_revisions (
  id                     TEXT PRIMARY KEY,
  skill_id               TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  version                TEXT NOT NULL,
  content_hash           TEXT NOT NULL,
  status                 TEXT NOT NULL
                           CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'superseded')),
  diff_summary           TEXT NOT NULL DEFAULT '',
  diff_stat_json         TEXT,
  storage_snapshot_path  TEXT,
  submitted_by           TEXT NOT NULL REFERENCES users(id),
  submitted_at           TEXT NOT NULL,
  reviewed_by            TEXT REFERENCES users(id),
  reviewed_at            TEXT,
  review_comment         TEXT,
  UNIQUE (skill_id, version)
);

CREATE INDEX IF NOT EXISTS idx_skill_revisions_status ON skill_revisions(status, submitted_at);

CREATE TABLE IF NOT EXISTS skill_grants (
  id              TEXT PRIMARY KEY,
  skill_id        TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  principal_type  TEXT NOT NULL CHECK (principal_type IN ('user', 'role')),
  principal_id    TEXT NOT NULL,
  perm            TEXT NOT NULL DEFAULT 'run' CHECK (perm IN ('run')),
  created_by      TEXT NOT NULL REFERENCES users(id),
  created_at      TEXT NOT NULL,
  UNIQUE (skill_id, principal_type, principal_id, perm)
);

CREATE INDEX IF NOT EXISTS idx_skill_grants_principal
  ON skill_grants(principal_type, principal_id);

CREATE TABLE IF NOT EXISTS chat_sessions (
  id                    TEXT PRIMARY KEY,
  user_id               TEXT NOT NULL REFERENCES users(id),
  title                 TEXT NOT NULL DEFAULT '新对话',
  status                TEXT NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'archived', 'error')),
  opencode_session_id   TEXT UNIQUE,
  work_dir_rel          TEXT NOT NULL,
  model_hint            TEXT,
  last_message_at       TEXT,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL,
  deleted_at            TEXT
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_list
  ON chat_sessions(user_id, deleted_at, last_message_at);

CREATE TABLE IF NOT EXISTS chat_messages (
  id                    TEXT PRIMARY KEY,
  chat_id               TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  user_id               TEXT NOT NULL,
  role                  TEXT NOT NULL
                          CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  seq                   INTEGER NOT NULL,
  content_text          TEXT,
  content_path          TEXT,
  content_sha256        TEXT,
  token_count_est       INTEGER,
  opencode_message_ref  TEXT,
  client_message_id     TEXT,
  created_at            TEXT NOT NULL,
  UNIQUE (chat_id, seq)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_messages_client_id
  ON chat_messages(chat_id, client_message_id)
  WHERE client_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_seq ON chat_messages(chat_id, seq);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_time ON chat_messages(user_id, created_at);

CREATE TABLE IF NOT EXISTS chat_attachments (
  id              TEXT PRIMARY KEY,
  chat_id         TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  user_id         TEXT NOT NULL,
  message_id      TEXT REFERENCES chat_messages(id) ON DELETE SET NULL,
  direction       TEXT NOT NULL CHECK (direction IN ('inbox', 'outbox')),
  original_name   TEXT NOT NULL,
  stored_rel_path TEXT NOT NULL,
  mime            TEXT,
  size_bytes      INTEGER NOT NULL,
  sha256          TEXT NOT NULL,
  created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_attachments_chat ON chat_attachments(chat_id, direction);
CREATE INDEX IF NOT EXISTS idx_chat_attachments_user ON chat_attachments(user_id, created_at);

CREATE TABLE IF NOT EXISTS jobs (
  id                   TEXT PRIMARY KEY,
  user_id              TEXT NOT NULL REFERENCES users(id),
  chat_id              TEXT REFERENCES chat_sessions(id) ON DELETE SET NULL,
  skill_id             TEXT REFERENCES skills(id) ON DELETE SET NULL,
  skill_key            TEXT NOT NULL,
  skill_version        TEXT NOT NULL,
  skill_content_hash   TEXT NOT NULL,
  status               TEXT NOT NULL
                         CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  error_message        TEXT,
  work_dir_rel         TEXT NOT NULL,
  created_at           TEXT NOT NULL,
  started_at           TEXT,
  finished_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);

CREATE TABLE IF NOT EXISTS audit_events (
  id              TEXT PRIMARY KEY,
  ts              TEXT NOT NULL,
  actor_user_id   TEXT,
  action          TEXT NOT NULL,
  resource_type   TEXT NOT NULL,
  resource_id     TEXT,
  chat_id         TEXT,
  job_id          TEXT,
  trace_id        TEXT,
  ip              TEXT,
  summary         TEXT NOT NULL,
  detail_json     TEXT,
  payload_sha256  TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events(ts);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor_user_id, ts);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action, ts);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_events(trace_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id             TEXT PRIMARY KEY,
  user_id        TEXT NOT NULL,
  key            TEXT NOT NULL,
  request_hash   TEXT NOT NULL,
  response_code  INTEGER NOT NULL,
  response_body  TEXT,
  created_at     TEXT NOT NULL,
  expires_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempo_expires ON idempotency_keys(expires_at);

-- Seed schema version (application also upserts)
INSERT OR IGNORE INTO schema_meta(key, value, updated_at)
VALUES ('version', '1', '1970-01-01T00:00:00.000Z');
