"""SOP tools — Agno Tool 定义（会话内待办管理）。"""

import json

from agno.run import RunContext
from agno.tools import tool


def _audit(run_context: RunContext, action: str, ok: bool, payload: dict) -> None:
    run_context.dependencies.setdefault("executed_actions", []).append(
        {"action": action, "ok": ok, "payload": payload}
    )


@tool(name="add_todo", description="添加当前会话的待办事项")
def add_todo(
    run_context: RunContext,
    title: str,
    detail: str = "",
    priority: int = 2,
    due_date: str = "",
    tags: str = "",
) -> str:
    manager = run_context.dependencies["todo_manager"]
    result = manager.add(
        session_id=run_context.session_id,
        title=title,
        detail=detail,
        priority=priority,
        due_date=due_date or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
    )
    _audit(run_context, "add", True, result)
    return json.dumps(result, ensure_ascii=False)


@tool(name="list_todos", description="列出当前会话的待办事项")
def list_todos(run_context: RunContext, status: str = "") -> str:
    manager = run_context.dependencies["todo_manager"]
    rows = manager.list(session_id=run_context.session_id, status=status or None)
    _audit(run_context, "list", True, {"count": len(rows)})
    return json.dumps(rows, ensure_ascii=False)


@tool(name="update_todo", description="更新当前会话的某个待办事项")
def update_todo(
    run_context: RunContext,
    todo_id: int,
    title: str = "",
    detail: str = "",
    priority: int = -1,
    due_date: str = "",
) -> str:
    manager = run_context.dependencies["todo_manager"]
    updates = {}
    if title:
        updates["title"] = title
    if detail:
        updates["detail"] = detail
    if priority >= 0:
        updates["priority"] = priority
    if due_date:
        updates["due_date"] = due_date
    ok = manager.update(
        session_id=run_context.session_id,
        todo_id=todo_id,
        updates=updates,
    )
    _audit(run_context, "update", ok, {"todo_id": todo_id})
    return json.dumps({"ok": ok}, ensure_ascii=False)


@tool(name="delete_todo", description="删除当前会话的某个待办事项")
def delete_todo(run_context: RunContext, todo_id: int) -> str:
    manager = run_context.dependencies["todo_manager"]
    ok = manager.delete(
        session_id=run_context.session_id,
        todo_id=todo_id,
    )
    _audit(run_context, "delete", ok, {"todo_id": todo_id})
    return json.dumps({"ok": ok}, ensure_ascii=False)


@tool(name="mark_done", description="标记当前会话的某个待办为已完成")
def mark_done(run_context: RunContext, todo_id: int) -> str:
    manager = run_context.dependencies["todo_manager"]
    ok = manager.set_status(
        session_id=run_context.session_id,
        todo_id=todo_id,
        status="done",
    )
    _audit(run_context, "mark_done", ok, {"todo_id": todo_id})
    return json.dumps({"ok": ok}, ensure_ascii=False)
