"""Chat route — POST / 和 POST /stream。"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api.schemas.chat import ChatRequest, ChatResponse
from app.core.agent_factory import create_chat_agent
from app.core.session_service import SessionAccessError, SessionModeMismatchError, SessionService
from app.deps import get_current_user_id, get_session_service

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    session_service: SessionService = Depends(get_session_service),
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        session_id = session_service.ensure_session(
            session_id=req.session_id,
            mode="chat",
            user_id=current_user_id,
        )
    except SessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except SessionModeMismatchError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    # 应用层知识检索
    knowledge_service = request.app.state.knowledge_service
    citations = await knowledge_service.search_references(req.message)

    # Agent 生成
    agent = create_chat_agent()
    run_response = await agent.arun(
        input=req.message,
        session_id=session_id,
        user_id=current_user_id,
        dependencies={"knowledge_refs": [c.model_dump() for c in citations]},
    )

    session_service.touch_session(session_id=session_id, user_id=current_user_id)

    # 提取回复内容
    content = run_response.content if isinstance(run_response.content, str) else str(run_response.content)

    return ChatResponse(
        session_id=session_id,
        message=content,
        grounded=bool(citations),
        citations=citations,
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    session_service: SessionService = Depends(get_session_service),
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        session_id = session_service.ensure_session(
            session_id=req.session_id,
            mode="chat",
            user_id=current_user_id,
        )
    except SessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except SessionModeMismatchError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    # 应用层知识检索
    knowledge_service = request.app.state.knowledge_service
    citations = await knowledge_service.search_references(req.message)

    agent = create_chat_agent()

    async def event_generator():
        try:
            # 先发送引用信息
            if citations:
                yield {
                    "event": "citations",
                    "data": json.dumps(
                        [c.model_dump() for c in citations],
                        ensure_ascii=False,
                    ),
                }

            # 流式调用 Agent — stream=True 返回 AsyncIterator[RunOutputEvent]
            stream_iter = agent.arun(
                input=req.message,
                session_id=session_id,
                user_id=current_user_id,
                dependencies={"knowledge_refs": [c.model_dump() for c in citations]},
                stream=True,
            )

            async for event in stream_iter:
                event_type = type(event).__name__

                if event_type == "RunContentEvent" and event.content:
                    text = event.content if isinstance(event.content, str) else str(event.content)
                    yield {
                        "event": "token",
                        "data": text,
                    }
                elif event_type == "ToolCallStartedEvent":
                    yield {
                        "event": "tool_call_started",
                        "data": json.dumps({"name": str(getattr(event, 'tool_call', ''))}, ensure_ascii=False),
                    }
                elif event_type == "ToolCallCompletedEvent":
                    yield {
                        "event": "tool_call_completed",
                        "data": json.dumps({"name": str(getattr(event, 'tool_call', ''))}, ensure_ascii=False),
                    }
                elif event_type == "RunErrorEvent":
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(event)}, ensure_ascii=False),
                    }
                # RunCompletedEvent: fall through to done

            yield {"event": "done", "data": json.dumps({"session_id": session_id})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}
        finally:
            session_service.touch_session(session_id=session_id, user_id=current_user_id)

    return EventSourceResponse(event_generator())
