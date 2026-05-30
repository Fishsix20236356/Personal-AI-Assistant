"""Session route — CRUD。"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.session import SessionInfo
from app.core.session_service import SessionAccessError, SessionService
from app.deps import get_current_user_id, get_session_service

router = APIRouter()


@router.get("/", response_model=list[SessionInfo])
async def list_sessions(
    mode: str | None = None,
    session_service: SessionService = Depends(get_session_service),
    current_user_id: str = Depends(get_current_user_id),
):
    rows = session_service.repo.list_sessions(mode=mode, user_id=current_user_id)
    return [
        SessionInfo(
            session_id=r["session_id"],
            mode=r["mode"],
            title=r["title"],
            is_archived=bool(r["is_archived"]),
            last_run_at=r.get("last_run_at"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
    current_user_id: str = Depends(get_current_user_id),
):
    r = session_service.repo.get_session(session_id, user_id=current_user_id)
    if not r:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(
        session_id=r["session_id"],
        mode=r["mode"],
        title=r["title"],
        is_archived=bool(r["is_archived"]),
        last_run_at=r.get("last_run_at"),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


@router.put("/{session_id}/rename")
async def rename_session(
    session_id: str,
    title: str,
    session_service: SessionService = Depends(get_session_service),
    current_user_id: str = Depends(get_current_user_id),
):
    r = session_service.repo.get_session(session_id, user_id=current_user_id)
    if not r:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session_service.rename_session(
            session_id=session_id,
            title=title,
            user_id=current_user_id,
        )
    except SessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return {"ok": True}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
    current_user_id: str = Depends(get_current_user_id),
):
    r = session_service.repo.get_session(session_id, user_id=current_user_id)
    if not r:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session_service.delete_session(session_id=session_id, user_id=current_user_id)
    except SessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return {"ok": True}
