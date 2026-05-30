"""WeChat tools — Agno Tool 定义。"""

import json

from agno.run import RunContext
from agno.tools import tool


@tool(name="search_messages", description="按关键词、联系人、群聊、时间范围综合搜索微信消息")
def search_messages(
    run_context: RunContext,
    query: str = "",
    contact: str = "",
    room: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 20,
) -> str:
    store = run_context.dependencies["wechat_search"]
    rows = store.search_messages(
        query=query,
        contact=contact,
        room=room,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return json.dumps(rows, ensure_ascii=False)


@tool(name="get_message_context", description="获取某条微信消息前后上下文")
def get_message_context(run_context: RunContext, msg_id: str, window: int = 5) -> str:
    store = run_context.dependencies["wechat_search"]
    rows = store.get_message_context(msg_id=msg_id, window=window)
    return json.dumps(rows, ensure_ascii=False)


@tool(name="list_contacts", description="搜索联系人列表")
def list_contacts(run_context: RunContext, keyword: str = "") -> str:
    store = run_context.dependencies["wechat_search"]
    return json.dumps(store.list_contacts(keyword=keyword), ensure_ascii=False)


@tool(name="list_rooms", description="搜索群聊列表")
def list_rooms(run_context: RunContext, keyword: str = "") -> str:
    store = run_context.dependencies["wechat_search"]
    return json.dumps(store.list_rooms(keyword=keyword), ensure_ascii=False)
