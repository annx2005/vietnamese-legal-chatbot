from fastapi import APIRouter
from app.api.routes import ingest

api_router = APIRouter()
api_router.include_router(ingest.router, prefix="/ingest", tags=["Document Ingestion"])
