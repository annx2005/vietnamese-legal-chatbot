import json

from sqlalchemy import Column, DateTime, Float, String, Text, func

from app.db.session import Base


class ChatLogRecord(Base):
    """SQLAlchemy model for persisting chat logs to PostgreSQL."""

    __tablename__ = "chat_logs"

    id = Column(String(64), primary_key=True, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    status = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    citations_json = Column(Text, nullable=False, default="[]")
    review_status = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def set_citations(self, citations: list) -> None:
        """Serialize a list of Citation dicts to JSON for storage."""
        self.citations_json = json.dumps(
            [c.model_dump() if hasattr(c, "model_dump") else c for c in citations],
            ensure_ascii=False,
        )

    def get_citations(self) -> list:
        """Deserialize stored JSON back into a list of dicts."""
        try:
            return json.loads(self.citations_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
