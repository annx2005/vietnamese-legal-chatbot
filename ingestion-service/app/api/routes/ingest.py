from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_admin
from app.schemas.ingest import (
    AdminStatsResponse,
    DocumentListResponse,
    DocumentRecord,
    IngestRequest,
    IngestResponse,
    JobListResponse,
)
from app.services.ingestion_service import IngestionService

router = APIRouter()

def get_ingestion_service() -> IngestionService:
    return IngestionService()

@router.post("/", response_model=IngestResponse, summary="Kích hoạt pipeline xử lý tài liệu")
async def start_ingestion(
    request: IngestRequest,
    _: None = Depends(require_admin),
    service: IngestionService = Depends(get_ingestion_service),
):
    return await service.trigger_ingestion(request)

@router.get("/jobs", response_model=JobListResponse, summary="Danh sách job ingestion")
async def list_jobs(_: None = Depends(require_admin), service: IngestionService = Depends(get_ingestion_service)):
    return JobListResponse(jobs=service.list_jobs())

@router.post("/jobs/{task_id}/retry", response_model=IngestResponse, summary="Retry job ingestion lỗi")
async def retry_job(
    task_id: str,
    _: None = Depends(require_admin),
    service: IngestionService = Depends(get_ingestion_service),
):
    response = await service.retry_job(task_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return response

@router.get("/documents", response_model=DocumentListResponse, summary="Danh sách tài liệu đã ingest")
async def list_documents(_: None = Depends(require_admin), service: IngestionService = Depends(get_ingestion_service)):
    return DocumentListResponse(documents=service.list_documents())

@router.post("/documents/{document_id}/disable", response_model=DocumentRecord, summary="Ẩn tài liệu khỏi kết quả RAG")
async def disable_document(
    document_id: str,
    _: None = Depends(require_admin),
    service: IngestionService = Depends(get_ingestion_service),
):
    document = service.disable_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.post("/documents/{document_id}/enable", response_model=DocumentRecord, summary="Hiển thị lại tài liệu trong kết quả RAG")
async def enable_document(
    document_id: str,
    _: None = Depends(require_admin),
    service: IngestionService = Depends(get_ingestion_service),
):
    document = service.enable_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.get("/admin/stats", response_model=AdminStatsResponse, summary="Thống kê ingestion cho admin")
async def admin_stats(_: None = Depends(require_admin), service: IngestionService = Depends(get_ingestion_service)):
    return service.admin_stats()

@router.get("/health", summary="Kiểm tra trạng thái dịch vụ Ingestion")
async def health_check():
    return {"status": "ok", "service": "ingestion-service", "pubsub": "connected"}
