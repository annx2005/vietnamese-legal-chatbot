from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.rag import get_rag_service
from app.core.auth import require_admin
from app.db.session import get_db
from app.schemas.rag import AdminRagStatsResponse, ChatLog, ChatLogListResponse, ReviewRequest
from app.services.rag_service import RAGService

router = APIRouter()


@router.get("/chat-logs", response_model=ChatLogListResponse, summary="Lịch sử hỏi đáp cho admin")
async def list_chat_logs(_: None = Depends(require_admin), service: RAGService = Depends(get_rag_service)):
    return ChatLogListResponse(logs=service.list_chat_logs())


@router.post("/chat-logs/{log_id}/review", response_model=ChatLog, summary="Đánh giá chất lượng câu trả lời")
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


@router.get("/stats", response_model=AdminRagStatsResponse, summary="Thống kê RAG cho admin")
async def admin_stats(_: None = Depends(require_admin), service: RAGService = Depends(get_rag_service)):
    return service.admin_stats()
