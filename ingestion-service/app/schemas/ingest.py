from pydantic import BaseModel
from typing import Optional

class IngestRequest(BaseModel):
    file_url: str
    document_type: str = "PDF"
    metadata: Optional[dict] = None

class IngestResponse(BaseModel):
    task_id: str
    status: str
    message: str
