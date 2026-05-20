from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.db.session import Base


class DocumentRecordModel(Base):
    """SQLAlchemy model for persisted ingestion documents."""

    __tablename__ = "documents"

    document_id = Column(String(64), primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    source_url = Column(Text, nullable=False)
    document_type = Column(String(32), nullable=False, default="PDF")
    domain = Column(String(128), nullable=False, default="general")
    effective_status = Column(String(64), nullable=False, default="unknown")
    enabled = Column(Boolean, nullable=False, default=True)
    chunks_count = Column(Integer, nullable=False, default=0)
    ingestion_status = Column(String(32), nullable=False, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IngestionJobRecord(Base):
    """SQLAlchemy model for persisted ingestion job history."""

    __tablename__ = "ingestion_jobs"

    task_id = Column(String(64), primary_key=True, index=True)
    document_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False)
    file_url = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    chunks_indexed = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
