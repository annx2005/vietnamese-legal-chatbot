from fastapi import APIRouter, Depends
from app.schemas.rag import QueryRequest, QueryResponse
from app.services.rag_service import RAGService

router = APIRouter()

def get_rag_service() -> RAGService:
    return RAGService()

@router.post("/query", response_model=QueryResponse, summary="Thực hiện truy vấn RAG")
async def perform_rag_query(request: QueryRequest, service: RAGService = Depends(get_rag_service)):
    return await service.query(request)

@router.get("/health", summary="Kiểm tra trạng thái dịch vụ RAG")
async def health_check():
    return {"status": "ok", "service": "rag-service", "vector_db": "connected"}
