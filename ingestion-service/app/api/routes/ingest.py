from fastapi import APIRouter, Depends
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.ingestion_service import IngestionService

router = APIRouter()

def get_ingestion_service() -> IngestionService:
    return IngestionService()

@router.post("/", response_model=IngestResponse, summary="Kích hoạt pipeline xử lý tài liệu")
async def start_ingestion(request: IngestRequest, service: IngestionService = Depends(get_ingestion_service)):
    return await service.trigger_ingestion(request)

@router.get("/health", summary="Kiểm tra trạng thái dịch vụ Ingestion")
async def health_check():
    return {"status": "ok", "service": "ingestion-service", "pubsub": "connected"}
