"""重建脚本：清空知识库并重新全量导入。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.app_meta import AppMetaRepository
from app.knowledge.tracker_repository import TrackerRepository
from app.knowledge.loader import KnowledgeLoader
from config.settings import settings


def main():
    AppMetaRepository(settings.APP_META_DB_PATH)
    tracker_repo = TrackerRepository(settings.APP_META_DB_PATH)
    loader = KnowledgeLoader(tracker_repo)

    print("Rebuilding knowledge base...")
    loader.rebuild_all()
    print("Done.")


if __name__ == "__main__":
    main()
