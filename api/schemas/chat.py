"""Chat API schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)


class Citation(BaseModel):
    content_id: str
    source: str
    snippet: str
    score: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    grounded: bool
    citations: list[Citation] = []
    uncertain_points: list[str] = []
    next_steps: list[str] = []


class ChatAgentOutput(BaseModel):
    answer: str = Field(description="给用户的最终回答")
    uncertain_points: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
