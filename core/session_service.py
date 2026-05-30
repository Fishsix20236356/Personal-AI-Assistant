"""Session service — 会话生命周期管理。"""

import uuid

from app.db.app_meta import AppMetaRepository


class SessionAccessError(Exception):
    pass


class SessionModeMismatchError(Exception):
    pass


class SessionService:
    def __init__(self, repo: AppMetaRepository):
        self.repo = repo

    def ensure_session(
        self, session_id: str | None, mode: str, user_id: str | None = None
    ) -> str:
        user_id = user_id or ""

        if session_id:
            existing = self.repo.get_session(session_id)
            if existing:
                if existing["mode"] != mode:
                    raise SessionModeMismatchError(
                        f"Session mode mismatch: expected {existing['mode']}, got {mode}"
                    )
                if (existing.get("user_id") or "") != user_id:
                    raise SessionAccessError("Session is not owned by current user")
                return session_id

        sid = session_id or f"{mode}_{uuid.uuid4().hex}"
        self.repo.upsert_session(
            session_id=sid, mode=mode, user_id=user_id
        )
        return sid

    def touch_session(
        self,
        session_id: str,
        title: str | None = None,
        user_id: str | None = None,
    ) -> None:
        self.repo.touch_session(session_id=session_id, title=title, user_id=user_id)

    def rename_session(
        self,
        session_id: str,
        title: str,
        user_id: str | None = None,
    ) -> None:
        ok = self.repo.rename_session(
            session_id=session_id,
            title=title,
            user_id=user_id,
        )
        if not ok:
            raise SessionAccessError("Session not found or access denied")

    def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        session = self.repo.get_session(session_id=session_id, user_id=user_id)
        if not session:
            raise SessionAccessError("Session not found or access denied")

        agent = self._agent_for_mode(session["mode"])
        agent.delete_session(session_id=session_id)
        self.repo.delete_session_cascade(session_id=session_id, user_id=user_id)

    def _agent_for_mode(self, mode: str):
        from app.core.agent_factory import create_chat_agent, create_wechat_agent, create_sop_agent

        if mode == "chat":
            return create_chat_agent()
        if mode == "wechat":
            return create_wechat_agent()
        return create_sop_agent()
