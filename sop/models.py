"""SOP models — 待办事项状态和优先级枚举。"""

from enum import Enum


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
