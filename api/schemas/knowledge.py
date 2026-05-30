"""Knowledge API schemas."""

from pydantic import BaseModel


class KnowledgeStatusResponse(BaseModel):
    total_documents: int
    total_chunks: int
    pending_files: int
    error_files: int
    last_sync_time: str | None = None
