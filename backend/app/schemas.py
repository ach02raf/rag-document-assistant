from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    id: UUID
    filename: str
    n_pages: int
    n_chunks: int
    created_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] | None = None  # None = tous les documents


class Source(BaseModel):
    document_id: UUID
    filename: str
    page: int
    snippet: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
