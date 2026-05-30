"""SOP API schemas."""

from enum import Enum

from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    PENDING = "pending"
    DOING = "doing"
    DONE = "done"
    CANCELLED = "cancelled"


class TodoPriority(int, Enum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TodoItem(BaseModel):
    id: int | None = None
    session_id: str
    title: str
    detail: str = ""
    priority: TodoPriority = TodoPriority.NORMAL
    status: TodoStatus = TodoStatus.PENDING
    due_date: str | None = None
    tags: list[str] = []
    created_at: str | None = None
    updated_at: str | None = None


class SopAction(BaseModel):
    action: str
    ok: bool
    payload: dict = Field(default_factory=dict)


class SopRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class SopResponse(BaseModel):
    session_id: str
    reply: str
    actions: list[SopAction] = []
    todos_snapshot: list[TodoItem] = []
