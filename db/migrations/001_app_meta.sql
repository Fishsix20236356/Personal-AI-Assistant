CREATE TABLE IF NOT EXISTS session_registry (
    session_id    TEXT PRIMARY KEY,
    mode          TEXT NOT NULL CHECK(mode IN ('chat', 'wechat', 'sop')),
    title         TEXT DEFAULT '',
    user_id       TEXT DEFAULT '',
    is_archived   INTEGER NOT NULL DEFAULT 0,
    last_run_at   TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_session_registry_mode
    ON session_registry(mode);

CREATE INDEX IF NOT EXISTS idx_session_registry_updated_at
    ON session_registry(updated_at DESC);


CREATE TABLE IF NOT EXISTS todos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    title         TEXT NOT NULL,
    detail        TEXT DEFAULT '',
    priority      INTEGER NOT NULL DEFAULT 2 CHECK(priority IN (0,1,2,3)),
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','doing','done','cancelled')),
    due_date      TEXT,
    tags_json     TEXT NOT NULL DEFAULT '[]',
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (session_id) REFERENCES session_registry(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_todos_session_status
    ON todos(session_id, status);

CREATE INDEX IF NOT EXISTS idx_todos_session_priority_due
    ON todos(session_id, priority, due_date);


CREATE TABLE IF NOT EXISTS doc_tracking (
    file_path        TEXT PRIMARY KEY,
    content_id       TEXT,
    file_hash        TEXT NOT NULL,
    file_size        INTEGER NOT NULL,
    chunk_count      INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL CHECK(status IN ('pending','synced','error')),
    last_synced_at   TEXT,
    last_error       TEXT DEFAULT '',
    created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);


CREATE TABLE IF NOT EXISTS daily_reports (
    report_date    TEXT PRIMARY KEY,
    summary_md     TEXT NOT NULL,
    source_sessions_json TEXT NOT NULL DEFAULT '[]',
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
