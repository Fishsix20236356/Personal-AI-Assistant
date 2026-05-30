"""AppMetaRepository — 业务元数据 CRUD（原生 sqlite3，不用 ORM）。"""

import sqlite3
from pathlib import Path


class AppMetaRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_tables(self) -> None:
        sql_path = Path(__file__).parent / "migrations" / "001_app_meta.sql"
        sql = sql_path.read_text(encoding="utf-8")
        with self._conn() as conn:
            conn.executescript(sql)

    # ── Session Registry ──────────────────────────────────────

    def upsert_session(
        self, session_id: str, mode: str, user_id: str = ""
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO session_registry (session_id, mode, user_id)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = datetime('now','localtime')
                """,
                (session_id, mode, user_id),
            )

    def touch_session(
        self,
        session_id: str,
        title: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        parts = ["last_run_at = datetime('now','localtime')"]
        params: list = []
        if title is not None:
            parts.append("title = ?")
            params.append(title)
        parts.append("updated_at = datetime('now','localtime')")
        params.append(session_id)

        sql = f"UPDATE session_registry SET {', '.join(parts)} WHERE session_id = ?"
        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)

        with self._conn() as conn:
            cur = conn.execute(sql, params)
        return cur.rowcount > 0

    def rename_session(
        self,
        session_id: str,
        title: str,
        user_id: str | None = None,
    ) -> bool:
        sql = """
            UPDATE session_registry
               SET title = ?, updated_at = datetime('now','localtime')
             WHERE session_id = ?
        """
        params: list = [title, session_id]
        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)

        with self._conn() as conn:
            cur = conn.execute(sql, params)
        return cur.rowcount > 0

    def delete_session_cascade(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> bool:
        sql = "DELETE FROM session_registry WHERE session_id = ?"
        params: list = [session_id]
        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)

        with self._conn() as conn:
            cur = conn.execute(sql, params)
        return cur.rowcount > 0

    def list_sessions(
        self,
        mode: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM session_registry WHERE 1=1"
        params: list = []
        if mode:
            sql += " AND mode = ?"
            params.append(mode)
        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)
        sql += " ORDER BY updated_at DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> dict | None:
        sql = "SELECT * FROM session_registry WHERE session_id = ?"
        params: list = [session_id]
        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)
        with self._conn() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
