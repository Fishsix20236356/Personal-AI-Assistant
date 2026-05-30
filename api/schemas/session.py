"""Session API schemas."""

from pydantic import BaseModel


class SessionInfo(BaseModel):
    session_id: str
    mode: str
    title: str
    is_archived: bool
    last_run_at: str | None = None
    created_at: str
    updated_at: str
