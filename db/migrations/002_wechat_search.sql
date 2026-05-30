CREATE TABLE IF NOT EXISTS wechat_messages (
    row_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_id         TEXT NOT NULL UNIQUE,
    talker         TEXT NOT NULL,
    talker_name    TEXT NOT NULL,
    room_id        TEXT DEFAULT '',
    room_name      TEXT DEFAULT '',
    content        TEXT NOT NULL,
    msg_type       INTEGER NOT NULL,
    ts             INTEGER NOT NULL,
    date_str       TEXT NOT NULL,
    is_self        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_wechat_messages_talker_ts
    ON wechat_messages(talker, ts DESC);

CREATE INDEX IF NOT EXISTS idx_wechat_messages_room_ts
    ON wechat_messages(room_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_wechat_messages_date_ts
    ON wechat_messages(date_str, ts DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS wechat_messages_fts USING fts5(
    content,
    talker_name,
    room_name,
    content='wechat_messages',
    content_rowid='row_id',
    tokenize='unicode61'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS wechat_messages_ai AFTER INSERT ON wechat_messages BEGIN
    INSERT INTO wechat_messages_fts(rowid, content, talker_name, room_name)
    VALUES (new.row_id, new.content, new.talker_name, new.room_name);
END;

CREATE TRIGGER IF NOT EXISTS wechat_messages_ad AFTER DELETE ON wechat_messages BEGIN
    INSERT INTO wechat_messages_fts(wechat_messages_fts, rowid, content, talker_name, room_name)
    VALUES ('delete', old.row_id, old.content, old.talker_name, old.room_name);
END;
