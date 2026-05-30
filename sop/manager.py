"""TodoManager — 待办事项 CRUD（会话隔离）。"""

import json
import sqlite3


class TodoManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def add(
        self,
        session_id: str,
        title: str,
        detail: str = "",
        priority: int = 2,
        due_date: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO todos (session_id, title, detail, priority, due_date, tags_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    title,
                    detail,
                    priority,
                    due_date,
                    json.dumps(tags or [], ensure_ascii=False),
                ),
            )
            return {"id": cursor.lastrowid}

    def update(self, session_id: str, todo_id: int, updates: dict) -> bool:
        allowed = {"title", "detail", "priority", "status", "due_date"}
        sets = []
        values = []
        for key, value in updates.items():
            if key in allowed:
                sets.append(f"{key} = ?")
                values.append(value)
        if not sets:
            return False
        sets.append("updated_at = datetime('now','localtime')")
        values.extend([session_id, todo_id])
        sql = f"UPDATE todos SET {', '.join(sets)} WHERE session_id = ? AND id = ?"
        with self._conn() as conn:
            cur = conn.execute(sql, values)
        return cur.rowcount > 0

    def delete(self, session_id: str, todo_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM todos WHERE session_id = ? AND id = ?",
                (session_id, todo_id),
            )
        return cur.rowcount > 0

    def set_status(self, session_id: str, todo_id: int, status: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE todos
                   SET status = ?, updated_at = datetime('now','localtime')
                 WHERE session_id = ? AND id = ?
                """,
                (status, session_id, todo_id),
            )
        return cur.rowcount > 0

    def list(self, session_id: str, status: str | None = None) -> list[dict]:
        sql = "SELECT * FROM todos WHERE session_id = ?"
        params: list = [session_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY priority ASC, due_date ASC, created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
