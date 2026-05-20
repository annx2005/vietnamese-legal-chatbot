import hashlib
import re
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatLogRecord
from app.schemas.rag import Citation, ChatLog, QueryRequest, QueryResponse, SourceDocument
from app.services.prompt_service import load_system_prompt, render_user_prompt
from app.services.vertex_ai_service import VertexAIService

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Document as QdrantDocument,
        FieldCondition,
        Filter,
        Fusion,
        FusionQuery,
        MatchValue,
        Modifier,
        Prefetch,
        SparseVectorConfig,
        SparseVectorNameConfig,
    )
except ImportError:  # pragma: no cover - dependency is present in the image
    QdrantClient = None
    QdrantDocument = None
    FieldCondition = None
    Filter = None
    Fusion = None
    FusionQuery = None
    MatchValue = None
    Modifier = None
    Prefetch = None
    SparseVectorConfig = None
    SparseVectorNameConfig = None


VERTEX_AI = VertexAIService()


def _embedding(text: str) -> List[float]:
    vector = [0.0] * settings.VECTOR_SIZE
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % settings.VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]


def _snippet(text: str, limit: int = 420) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _qdrant_client_kwargs() -> dict:
    kwargs = {}
    if settings.QDRANT_URL:
        kwargs["url"] = settings.QDRANT_URL
    else:
        kwargs["host"] = settings.QDRANT_HOST
        kwargs["port"] = settings.QDRANT_PORT
    if settings.QDRANT_API_KEY:
        kwargs["api_key"] = settings.QDRANT_API_KEY
    return kwargs


def _bm25_query_document(query: str):
    return QdrantDocument(
        text=query,
        model="qdrant/bm25",
        options={
            "language": settings.BM25_LANGUAGE,
            "tokenizer": settings.BM25_TOKENIZER,
            "ascii_folding": settings.BM25_ASCII_FOLDING,
        },
    )


def _sparse_vector_name_config():
    return SparseVectorNameConfig(
        sparse=SparseVectorConfig(modifier=Modifier.IDF),
    )


class RAGService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.qdrant = None
        if QdrantClient is not None:
            self.qdrant = QdrantClient(**_qdrant_client_kwargs())

    async def query(self, request: QueryRequest) -> QueryResponse:
        sources = self._retrieve(request)
        citations = [self._citation_from_source(source) for source in sources]
        confidence = max((source.score for source in sources), default=0.0)
        status = "answered" if confidence >= settings.CONFIDENCE_THRESHOLD and citations else "low_confidence"
        answer = self._compose_answer(request.query, citations, status)
        response = QueryResponse(
            answer=answer,
            sources=sources,
            citations=citations,
            confidence=round(confidence, 3),
            disclaimer=settings.DEFAULT_DISCLAIMER,
            status=status,
        )
        self._save_chat_log(request.query, response)
        return response

    def list_chat_logs(self) -> List[ChatLog]:
        if self.db is None:
            return []
        rows = (
            self.db.query(ChatLogRecord)
            .order_by(ChatLogRecord.created_at.desc())
            .all()
        )
        return [self._row_to_chat_log(row) for row in rows]

    def review_chat_log(self, log_id: str, review_status: str) -> Optional[ChatLog]:
        if self.db is None:
            return None
        row = self.db.query(ChatLogRecord).filter(ChatLogRecord.id == log_id).first()
        if row is None:
            return None
        row.review_status = review_status
        self.db.commit()
        self.db.refresh(row)
        return self._row_to_chat_log(row)

    def admin_stats(self) -> dict:
        if self.db is None:
            return {
                "chat_logs_total": 0,
                "low_confidence_total": 0,
                "reviewed_total": 0,
                "service_status": "ok",
            }
        total = self.db.query(ChatLogRecord).count()
        low = self.db.query(ChatLogRecord).filter(ChatLogRecord.status == "low_confidence").count()
        reviewed = self.db.query(ChatLogRecord).filter(ChatLogRecord.review_status.isnot(None)).count()
        return {
            "chat_logs_total": total,
            "low_confidence_total": low,
            "reviewed_total": reviewed,
            "service_status": "ok",
        }

    def _retrieve(self, request: QueryRequest) -> List[SourceDocument]:
        if self.qdrant is None:
            return self._fallback_sources(request)
        query_text = request.query.strip()
        if not query_text:
            return []
        query_filter = self._build_filter(request.filters or {})

        if self._search_mode() == "hybrid" and self._ensure_sparse_vector_schema():
            try:
                return self._hybrid_sources(query_text, query_filter, request.top_k)
            except Exception:
                pass

        try:
            hits = self._semantic_search(query_text, query_filter, request.top_k)
        except Exception:
            return self._fallback_sources(request)
        return self._sources_from_hits(hits, request.top_k, "semantic")

    def _semantic_search(self, query: str, query_filter, top_k: int):
        embedded_query = self._embed_query(query)
        if hasattr(self.qdrant, "query_points"):
            result = self.qdrant.query_points(
                collection_name=settings.COLLECTION_NAME,
                query=embedded_query,
                query_filter=query_filter,
                limit=max(top_k, 1),
                with_payload=True,
            )
            return result.points
        return self.qdrant.search(
            collection_name=settings.COLLECTION_NAME,
            query_vector=embedded_query,
            query_filter=query_filter,
            limit=max(top_k, 1),
            with_payload=True,
        )

    def _hybrid_sources(self, query: str, query_filter, top_k: int) -> List[SourceDocument]:
        dense_prefetch_limit = max(top_k, top_k * max(settings.HYBRID_DENSE_PREFETCH_MULTIPLIER, 1))
        sparse_prefetch_limit = max(top_k, top_k * max(settings.HYBRID_SPARSE_PREFETCH_MULTIPLIER, 1))
        result = self.qdrant.query_points(
            collection_name=settings.COLLECTION_NAME,
            prefetch=[
                Prefetch(
                    query=self._embed_query(query),
                    limit=dense_prefetch_limit,
                ),
                Prefetch(
                    query=_bm25_query_document(query),
                    using=settings.QDRANT_SPARSE_VECTOR_NAME,
                    limit=sparse_prefetch_limit,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=query_filter,
            limit=max(top_k, 1),
            with_payload=True,
        )
        return self._sources_from_hits(result.points, top_k, "hybrid")

    def _ensure_sparse_vector_schema(self) -> bool:
        if (
            self.qdrant is None
            or SparseVectorNameConfig is None
            or SparseVectorConfig is None
            or Modifier is None
        ):
            return False
        try:
            collection_info = self.qdrant.get_collection(settings.COLLECTION_NAME)
        except Exception:
            return False

        sparse_vectors = getattr(collection_info.config.params, "sparse_vectors", None) or {}
        if settings.QDRANT_SPARSE_VECTOR_NAME in sparse_vectors:
            return True

        try:
            self.qdrant.create_vector_name(
                collection_name=settings.COLLECTION_NAME,
                vector_name=settings.QDRANT_SPARSE_VECTOR_NAME,
                vector_name_config=_sparse_vector_name_config(),
            )
            return True
        except Exception:
            try:
                refreshed = self.qdrant.get_collection(settings.COLLECTION_NAME)
            except Exception:
                return False
            sparse_vectors = getattr(refreshed.config.params, "sparse_vectors", None) or {}
            return settings.QDRANT_SPARSE_VECTOR_NAME in sparse_vectors

    @staticmethod
    def _search_mode() -> str:
        mode = settings.SEARCH_MODE.strip().lower()
        if mode in {"semantic", "hybrid"}:
            return mode
        return "hybrid"

    def _sources_from_hits(self, hits, top_k: int, search_mode: str) -> List[SourceDocument]:
        sources: List[SourceDocument] = []
        for hit in hits:
            payload = hit.payload or {}
            if payload.get("enabled") is False:
                continue
            metadata = dict(payload)
            metadata["search_mode"] = search_mode
            metadata["search_scores"] = {search_mode: round(float(hit.score or 0.0), 6)}
            content = str(payload.get("content", ""))
            sources.append(
                SourceDocument(
                    id=str(hit.id),
                    content=content,
                    score=float(hit.score or 0.0),
                    metadata=metadata,
                )
            )
        return sources[: max(top_k, 1)]

    def _build_filter(self, filters: dict):
        conditions = []
        if not filters or Filter is None:
            return None
        for key in ("domain", "document_id", "effective_status"):
            value = filters.get(key)
            if value:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=conditions) if conditions else None

    def _fallback_sources(self, request: QueryRequest) -> List[SourceDocument]:
        if not request.query.strip():
            return []
        return [
            SourceDocument(
                id="demo-civil-code",
                content=(
                    "Nguồn demo: Khi chưa có tài liệu được ingest vào Qdrant, hệ thống chỉ có thể "
                    "minh họa cách trả lời có dẫn nguồn. Hãy upload và ingest văn bản pháp luật để có "
                    "kết quả chính xác theo corpus của bạn."
                ),
                score=0.12,
                metadata={
                    "title": "Demo corpus placeholder",
                    "source_url": "",
                    "domain": "general",
                    "article": "",
                    "effective_status": "unknown",
                },
            )
        ]

    def _citation_from_source(self, source: SourceDocument) -> Citation:
        metadata = source.metadata or {}
        return Citation(
            title=str(metadata.get("title") or "Nguồn chưa đặt tên"),
            article=str(metadata.get("article") or "") or None,
            snippet=_snippet(source.content),
            source_url=str(metadata.get("source_url") or "") or None,
            score=round(source.score, 3),
        )

    def _compose_answer(self, query: str, citations: List[Citation], status: str) -> str:
        if status == "low_confidence":
            return (
                "Mình chưa có đủ căn cứ trong dữ liệu hiện tại để kết luận chắc chắn. "
                "Bạn có thể upload thêm văn bản liên quan hoặc hỏi cụ thể hơn về lĩnh vực, điều luật, thời điểm áp dụng."
            )
        try:
            return VERTEX_AI.generate_answer(
                system_prompt=load_system_prompt(),
                user_prompt=render_user_prompt(query, citations),
            )
        except Exception:
            pass
        return self._compose_fallback_answer(query, citations)

    def _compose_fallback_answer(self, query: str, citations: List[Citation]) -> str:
        cited = "\n".join(
            f"- {citation.title}{f' ({citation.article})' if citation.article else ''}: {citation.snippet}"
            for citation in citations[:3]
        )
        return (
            f"Dựa trên các nguồn đã tìm thấy, câu hỏi \u201c{query}\u201d có thể được tra cứu theo các căn cứ sau:\n"
            f"{cited}\n\n"
            "Bạn nên kiểm tra tình trạng hiệu lực của văn bản và bối cảnh vụ việc cụ thể trước khi áp dụng."
        )

    def _embed_query(self, query: str) -> List[float]:
        try:
            return VERTEX_AI.embed_query(query)
        except Exception:
            return _embedding(query)

    def _save_chat_log(self, query: str, response: QueryResponse) -> None:
        log_id = f"log_{uuid.uuid4().hex[:12]}"
        if self.db is not None:
            record = ChatLogRecord(
                id=log_id,
                query=query,
                answer=response.answer,
                status=response.status,
                confidence=response.confidence,
            )
            record.set_citations(response.citations)
            self.db.add(record)
            self.db.commit()

    @staticmethod
    def _row_to_chat_log(row: ChatLogRecord) -> ChatLog:
        return ChatLog(
            id=row.id,
            query=row.query,
            answer=row.answer,
            status=row.status,
            confidence=row.confidence,
            citations=[Citation(**c) for c in row.get_citations()],
            review_status=row.review_status,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
