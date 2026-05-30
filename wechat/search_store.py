"""WeChat search store — FTS5 全文检索。"""

import sqlite3
from pathlib import Path


class WeChatSearchStore:
    def __init__(self, raw_db_path: str, search_db_path: str):
        self.raw_db_path = raw_db_path
        self.search_db_path = search_db_path
        Path(search_db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.search_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        sql_path = Path(__file__).parent.parent / "db" / "migrations" / "002_wechat_search.sql"
        if sql_path.exists():
            sql = sql_path.read_text(encoding="utf-8")
            with self._conn() as conn:
                conn.executescript(sql)

    def sync_incremental(self) -> int:
        """从微信原始库增量抽取消息到搜索库。返回新增条数。"""
        if not Path(self.raw_db_path).exists():
            return 0

        # 获取水位
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(ts) as max_ts FROM wechat_messages"
            ).fetchone()
            watermark = row["max_ts"] if row and row["max_ts"] else 0

        # 从原始库读取新消息
        raw_conn = sqlite3.connect(self.raw_db_path)
        raw_conn.row_factory = sqlite3.Row

        # 尝试读取微信原始表（字段名可能不同，这里做适配）
        try:
            rows = raw_conn.execute(
                """
                SELECT
                    msgId as msg_id,
                    talker,
                    CASE
                        WHEN message_type = 1 THEN content
                        ELSE ''
                    END as content,
                    createTime as ts,
                    type as msg_type
                FROM MSG
                WHERE createTime > ?
                ORDER BY createTime ASC
                """,
                (watermark,),
            ).fetchall()
        except Exception:
            raw_conn.close()
            return 0

        if not rows:
            raw_conn.close()
            return 0

        count = 0
        with self._conn() as conn:
            for r in rows:
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO wechat_messages
                            (msg_id, talker, talker_name, room_id, room_name,
                             content, msg_type, ts, date_str, is_self)
                        VALUES (?, ?, ?, '', '', ?, ?, ?, date(?, 'unixepoch', 'localtime'), 0)
                        """,
                        (
                            str(r["msg_id"]),
                            r["talker"],
                            r["talker"],
                            r["content"],
                            r["msg_type"],
                            r["ts"],
                            r["ts"],
                        ),
                    )
                    count += 1
                except Exception:
                    continue

        raw_conn.close()
        return count

    def search_messages(
        self,
        query: str = "",
        contact: str = "",
        room: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """搜索微信消息。query 非空时走 FTS5，否则走普通过滤。"""
        with self._conn() as conn:
            if query:
                # FTS5 全文搜索 + 条件过滤
                safe_query = self._escape_fts(query)
                sql = """
                    SELECT m.* FROM wechat_messages m
                    JOIN wechat_messages_fts f ON f.rowid = m.row_id
                    WHERE wechat_messages_fts MATCH ?
                """
                params: list = [safe_query]
            else:
                sql = "SELECT m.* FROM wechat_messages m WHERE 1=1"
                params = []

            if contact:
                sql += " AND m.talker_name LIKE ?"
                params.append(f"%{contact}%")
            if room:
                sql += " AND m.room_name LIKE ?"
                params.append(f"%{room}%")
            if start_date:
                sql += " AND m.date_str >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND m.date_str <= ?"
                params.append(end_date)

            sql += " ORDER BY m.ts DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_message_context(self, msg_id: str, window: int = 5) -> list[dict]:
        """获取某条消息前后上下文。"""
        with self._conn() as conn:
            # 定位消息
            msg = conn.execute(
                "SELECT * FROM wechat_messages WHERE msg_id = ?",
                (msg_id,),
            ).fetchone()
            if not msg:
                return []

            # 获取同会话前后消息
            talker = msg["talker"]
            room_id = msg["room_id"]
            ts = msg["ts"]

            if room_id:
                filter_sql = "room_id = ?"
                filter_val = room_id
            else:
                filter_sql = "talker = ?"
                filter_val = talker

            rows = conn.execute(
                f"""
                SELECT * FROM wechat_messages
                WHERE {filter_sql} = ?
                  AND ts BETWEEN ? AND ?
                ORDER BY ts ASC
                LIMIT ?
                """,
                (
                    filter_val,
                    ts - 3600,
                    ts + 3600,
                    window * 2 + 1,
                ),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_contacts(self, keyword: str = "") -> list[dict]:
        """搜索联系人。"""
        with self._conn() as conn:
            if keyword:
                rows = conn.execute(
                    """
                    SELECT talker, talker_name, MAX(ts) as last_ts
                    FROM wechat_messages
                    WHERE talker_name LIKE ? AND room_id = ''
                    GROUP BY talker
                    ORDER BY last_ts DESC
                    LIMIT 20
                    """,
                    (f"%{keyword}%",),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT talker, talker_name, MAX(ts) as last_ts
                    FROM wechat_messages
                    WHERE room_id = ''
                    GROUP BY talker
                    ORDER BY last_ts DESC
                    LIMIT 20
                    """,
                ).fetchall()
        return [dict(r) for r in rows]

    def list_rooms(self, keyword: str = "") -> list[dict]:
        """搜索群聊。"""
        with self._conn() as conn:
            if keyword:
                rows = conn.execute(
                    """
                    SELECT room_id, room_name, MAX(ts) as last_ts, COUNT(*) as msg_count
                    FROM wechat_messages
                    WHERE room_id != '' AND room_name LIKE ?
                    GROUP BY room_id
                    ORDER BY last_ts DESC
                    LIMIT 20
                    """,
                    (f"%{keyword}%",),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT room_id, room_name, MAX(ts) as last_ts, COUNT(*) as msg_count
                    FROM wechat_messages
                    WHERE room_id != ''
                    GROUP BY room_id
                    ORDER BY last_ts DESC
                    LIMIT 20
                    """,
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _escape_fts(query: str) -> str:
        """转义 FTS5 特殊字符。"""
        # 移除可能导致 FTS5 语法错误的字符
        chars_to_remove = '"*(){}[]:'
        for ch in chars_to_remove:
            query = query.replace(ch, " ")
        # 用 AND 连接各个词
        tokens = query.split()
        return " AND ".join(f'"{t}"' for t in tokens if t)
