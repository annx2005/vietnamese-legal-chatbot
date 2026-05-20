from pydantic import BaseModel, Field
from typing import List, Optional

class IngestRequest(BaseModel):
    file_url: Optional[str] = None
    document_id: Optional[str] = None
    document_type: str = "PDF"
    metadata: Optional[dict] = None

class IngestResponse(BaseModel):
    task_id: str
    status: str
    message: str
    document_id: Optional[str] = None
    chunks_indexed: int = 0

class DocumentRecord(BaseModel):
    document_id: str
    title: str
    source_url: str
    document_type: str = "PDF"
    domain: str = "general"
    effective_status: str = "unknown"
    enabled: bool = True
    chunks_count: int = 0
    ingestion_status: str = "queued"
    created_at: str
    updated_at: str

class IngestionJob(BaseModel):
    task_id: str
    document_id: str
    status: str
    file_url: str
    message: str
    chunks_indexed: int = 0
    error: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None

class JobListResponse(BaseModel):
    jobs: List[IngestionJob]

class DocumentListResponse(BaseModel):
    documents: List[DocumentRecord]

class AdminStatsResponse(BaseModel):
    documents_total: int
    chunks_total: int
    jobs_failed: int
    jobs_processing: int
    service_status: str = Field(default="ok")


class DocumentUploadedEvent(BaseModel):
    documentId: str
    fileName: str
    originalFileName: str
    gcsUrl: str
    documentType: str = "PDF"
    sizeBytes: int
    contentType: str
    uploadedAtEpoch: int


class PubSubPushMessage(BaseModel):
    data: str
    messageId: Optional[str] = None
    publishTime: Optional[str] = None
    attributes: Optional[dict[str, str]] = None


class PubSubPushEnvelope(BaseModel):
    message: PubSubPushMessage
    subscription: Optional[str] = None
