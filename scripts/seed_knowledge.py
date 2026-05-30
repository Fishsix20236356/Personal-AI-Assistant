"""初始化脚本：扫描 data/documents/ 导入知识库。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.app_meta import AppMetaRepository
from app.knowledge.tracker_repository import TrackerRepository
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.reader_factory import SUPPORTED_EXTENSIONS
from config.settings import settings


def main():
    # 确保 app_meta.db 存在
    AppMetaRepository(settings.APP_META_DB_PATH)

    tracker_repo = TrackerRepository(settings.APP_META_DB_PATH)
    loader = KnowledgeLoader(tracker_repo)

    docs_dir = Path(settings.WATCH_DIR)
    if not docs_dir.exists():
        print(f"Documents directory not found: {docs_dir}")
        return

    count = 0
    for path in docs_dir.rglob("*"):
        if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file():
            print(f"Ingesting: {path.name} ... ", end="", flush=True)
            result = loader.ingest(str(path))
            print(result["status"])
            count += 1

    print(f"\nDone. Processed {count} files.")


if __name__ == "__main__":
    main()
