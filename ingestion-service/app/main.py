from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.errors import IngestionException, ingestion_exception_handler, general_exception_handler
from app.db.models import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(IngestionException, ingestion_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API router mapped via application.yml context path /api/v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/", summary="Root endpoint")
def read_root():
    return {"status": "Ingestion Service is running"}
