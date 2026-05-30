"""构建微信搜索库脚本。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.wechat.search_store import WeChatSearchStore
from config.settings import settings


def main():
    store = WeChatSearchStore(
        raw_db_path=settings.WECHAT_RAW_DB_PATH,
        search_db_path=settings.WECHAT_SEARCH_DB_PATH,
    )
    count = store.sync_incremental()
    print(f"WeChat search DB built at: {settings.WECHAT_SEARCH_DB_PATH}")
    print(f"Synced {count} messages.")


if __name__ == "__main__":
    main()
