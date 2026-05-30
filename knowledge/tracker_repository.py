"""Tracker repository — 操作 doc_tracking 表（原生 sqlite3）。"""

import sqlite3


class TrackerRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, file_path: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM doc_tracking WHERE file_path = ?",
                (file_path,),
            ).fetchone()
        return dict(row) if row else None

    def upsert(
        self,
        file_path: str,
        content_id: str | None,
        file_hash: str,
        file_size: int,
        chunk_count: int = 0,
        status: str = "pending",
        last_error: str = "",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO doc_tracking
                    (file_path, content_id, file_hash, file_size, chunk_count,
                     status, last_synced_at, last_error)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'), ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    content_id = excluded.content_id,
                    file_hash = excluded.file_hash,
                    file_size = excluded.file_size,
                    chunk_count = excluded.chunk_count,
                    status = excluded.status,
                    last_synced_at = datetime('now','localtime'),
                    last_error = excluded.last_error,
                    updated_at = datetime('now','localtime')
                """,
                (file_path, content_id, file_hash, file_size, chunk_count, status, last_error),
            )

    def delete(self, file_path: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM doc_tracking WHERE file_path = ?",
                (file_path,),
            )

    def delete_all(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM doc_tracking")

    def count_by_status(self, status: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM doc_tracking WHERE status = ?",
                (status,),
            ).fetchone()
        return row["cnt"] if row else 0

    def get_last_sync_time(self) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(last_synced_at) as t FROM doc_tracking WHERE status = 'synced'"
            ).fetchone()
        return row["t"] if row and row["t"] else None

    def list_all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM doc_tracking ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
