"""初始化 app_meta.db：执行迁移 SQL 并建表。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.app_meta import AppMetaRepository
from config.settings import settings


def main():
    repo = AppMetaRepository(settings.APP_META_DB_PATH)
    sessions = repo.list_sessions()
    print(f"app_meta.db initialized at: {settings.APP_META_DB_PATH}")
    print(f"Existing sessions: {len(sessions)}")


if __name__ == "__main__":
    main()
