from fastapi import APIRouter
from app.api.routes import admin, rag

api_router = APIRouter()
api_router.include_router(rag.router, prefix="/rag", tags=["RAG Query"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
