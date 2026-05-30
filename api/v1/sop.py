"""SOP route — POST /。"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.sop import SopRequest, SopResponse, SopAction, TodoItem
from app.core.agent_factory import create_sop_agent
from app.core.session_service import SessionAccessError, SessionModeMismatchError, SessionService
from app.deps import get_current_user_id, get_session_service, get_todo_manager
from app.sop.manager import TodoManager
from app.sop.tools import add_todo, list_todos, update_todo, delete_todo, mark_done

router = APIRouter()


@router.post("/", response_model=SopResponse)
async def sop(
    req: SopRequest,
    session_service: SessionService = Depends(get_session_service),
    todo_manager: TodoManager = Depends(get_todo_manager),
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        session_id = session_service.ensure_session(
            session_id=req.session_id,
            mode="sop",
            user_id=current_user_id,
        )
    except SessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except SessionModeMismatchError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    executed_actions: list[dict] = []
    agent = create_sop_agent(tools=[add_todo, list_todos, update_todo, delete_todo, mark_done])

    run_response = await agent.arun(
        input=req.message,
        session_id=session_id,
        user_id=current_user_id,
        dependencies={
            "todo_manager": todo_manager,
            "executed_actions": executed_actions,
        },
    )

    session_service.touch_session(session_id=session_id, user_id=current_user_id)

    content = run_response.content if isinstance(run_response.content, str) else str(run_response.content)

    # 获取最新的 todo snapshot
    todos_raw = todo_manager.list(session_id=session_id)
    todos_snapshot = [
        TodoItem(
            id=t["id"],
            session_id=t["session_id"],
            title=t["title"],
            detail=t["detail"],
            priority=t["priority"],
            status=t["status"],
            due_date=t["due_date"],
            tags=__import__("json").loads(t.get("tags_json", "[]")),
            created_at=t["created_at"],
            updated_at=t["updated_at"],
        )
        for t in todos_raw
    ]

    actions = [SopAction(**a) for a in executed_actions]

    return SopResponse(
        session_id=session_id,
        reply=content,
        actions=actions,
        todos_snapshot=todos_snapshot,
    )
