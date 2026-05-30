"""WeChat route — POST /search。"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.wechat import WeChatSearchRequest, WeChatSearchResponse
from app.core.agent_factory import create_wechat_agent
from app.core.session_service import SessionAccessError, SessionModeMismatchError, SessionService
from app.deps import get_current_user_id, get_session_service, get_wechat_search
from app.wechat.search_store import WeChatSearchStore
from app.wechat.tools import search_messages, get_message_context, list_contacts, list_rooms

router = APIRouter()


@router.post("/search", response_model=WeChatSearchResponse)
async def wechat_search(
    req: WeChatSearchRequest,
    session_service: SessionService = Depends(get_session_service),
    wechat_search: WeChatSearchStore = Depends(get_wechat_search),
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        session_id = session_service.ensure_session(
            session_id=req.session_id,
            mode="wechat",
            user_id=current_user_id,
        )
    except SessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except SessionModeMismatchError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    agent = create_wechat_agent(
        tools=[search_messages, get_message_context, list_contacts, list_rooms]
    )

    run_response = await agent.arun(
        input=req.query,
        session_id=session_id,
        user_id=current_user_id,
        dependencies={"wechat_search": wechat_search},
    )

    session_service.touch_session(session_id=session_id, user_id=current_user_id)

    content = run_response.content if isinstance(run_response.content, str) else str(run_response.content)

    return WeChatSearchResponse(
        session_id=session_id,
        answer=content,
        total_count=0,
    )
