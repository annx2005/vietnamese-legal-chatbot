from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: Optional[dict] = None

class SourceDocument(BaseModel):
    id: str
    content: str
    score: float
    metadata: Optional[dict] = None

class Citation(BaseModel):
    title: str = "Nguồn chưa đặt tên"
    article: Optional[str] = None
    snippet: str
    source_url: Optional[str] = None
    score: float = 0

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = 0
    disclaimer: str
    status: str = "answered"

class ChatLog(BaseModel):
    id: str
    query: str
    answer: str
    status: str
    confidence: float
    citations: List[Citation]
    review_status: Optional[str] = None
    created_at: str

class ChatLogListResponse(BaseModel):
    logs: List[ChatLog]

class ReviewRequest(BaseModel):
    review_status: str

class AdminRagStatsResponse(BaseModel):
    chat_logs_total: int
    low_confidence_total: int
    reviewed_total: int
    service_status: str = "ok"
