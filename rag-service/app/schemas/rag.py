from pydantic import BaseModel
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

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
