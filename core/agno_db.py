"""Agno Session DB — 使用 SqliteDb 管理会话历史。"""

from agno.db.sqlite import SqliteDb
from config.settings import settings


def build_agno_db() -> SqliteDb:
    return SqliteDb(
        db_file=settings.AGNO_DB_PATH,
        session_table="agent_sessions",
    )
