from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.session import get_db
from app.schemas.rag import (
    AdminRagStatsResponse,
    ChatLog,
    ChatLogListResponse,
    QueryRequest,
    QueryResponse,
    ReviewRequest,
)
from app.services.rag_service import RAGService

router = APIRouter()

def get_rag_service(db: Session = Depends(get_db)) -> RAGService:
    return RAGService(db=db)

@router.post("/query", response_model=QueryResponse, summary="Thực hiện truy vấn RAG")
async def perform_rag_query(request: QueryRequest, service: RAGService = Depends(get_rag_service)):
    return await service.query(request)

@router.get("/admin/chat-logs", response_model=ChatLogListResponse, summary="Lịch sử hỏi đáp cho admin")
async def list_chat_logs(_: None = Depends(require_admin), service: RAGService = Depends(get_rag_service)):
    return ChatLogListResponse(logs=service.list_chat_logs())

@router.post("/admin/chat-logs/{log_id}/review", response_model=ChatLog, summary="Đánh giá chất lượng câu trả lời")
async def review_chat_log(
    log_id: str,
    request: ReviewRequest,
    _: None = Depends(require_admin),
    service: RAGService = Depends(get_rag_service),
):
    log = service.review_chat_log(log_id, request.review_status)
    if log is None:
        raise HTTPException(status_code=404, detail="Chat log not found")
    return log

@router.get("/admin/stats", response_model=AdminRagStatsResponse, summary="Thống kê RAG cho admin")
async def admin_stats(_: None = Depends(require_admin), service: RAGService = Depends(get_rag_service)):
    return service.admin_stats()

@router.get("/health", summary="Kiểm tra trạng thái dịch vụ RAG")
async def health_check():
    return {"status": "ok", "service": "rag-service", "vector_db": "connected"}
