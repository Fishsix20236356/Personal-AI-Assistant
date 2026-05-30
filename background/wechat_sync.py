"""WeChat incremental sync background task."""

import asyncio

from app.wechat.search_store import WeChatSearchStore


async def run_wechat_sync(wechat_search: WeChatSearchStore) -> int:
    """执行微信增量同步。"""
    return await asyncio.to_thread(wechat_search.sync_incremental)

__all__ = ["run_wechat_sync"]
