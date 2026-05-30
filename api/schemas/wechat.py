"""WeChat API schemas."""

from pydantic import BaseModel, Field


class WeChatSearchRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    query: str = Field(..., min_length=1, max_length=2000)


class WeChatMessageOut(BaseModel):
    msg_id: str
    talker_name: str
    room_name: str | None = None
    content: str
    timestamp: int
    date_str: str
    is_self: bool


class WeChatSearchResponse(BaseModel):
    session_id: str
    answer: str
    messages: list[WeChatMessageOut] = []
    total_count: int = 0
