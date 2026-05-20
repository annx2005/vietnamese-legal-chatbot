import hashlib
import io
import json
import re
import uuid
from base64 import b64decode
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DocumentRecordModel, IngestionJobRecord
from app.schemas.ingest import (
    DocumentRecord,
    DocumentUploadedEvent,
    IngestRequest,
    IngestResponse,
    IngestionJob,
    PubSubPushEnvelope,
)
from app.services.qdrant_sparse import (
    build_bm25_document,
    build_sparse_text,
    ensure_sparse_collection_schema,
    estimate_bm25_avg_len,
    sparse_vector_name,
)
from app.services.vertex_ai_service import VertexAIEmbeddingService

try:
    import pdfplumber
except ImportError:  # pragma: no cover - dependency is present in the image
    pdfplumber = None

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - dependency is present in the image
    storage = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue, PointStruct
except ImportError:  # pragma: no cover - dependency is present in the image
    QdrantClient = None
    FieldCondition = None
    Filter = None
    MatchValue = None
    PointStruct = None


VERTEX_EMBEDDINGS = VertexAIEmbeddingService()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _embedding(text: str) -> List[float]:
    """Deterministic local embedding so the MVP works without external AI keys."""
    vector = [0.0] * settings.VECTOR_SIZE
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % settings.VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]


def _title_from_request(request: IngestRequest) -> str:
    if request.metadata and request.metadata.get("title"):
        return str(request.metadata["title"])
    if request.file_url:
        path = urlparse(request.file_url).path
        return path.rsplit("/", 1)[-1] or "Legal document"
    return "Legal document"


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


class IngestionService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.qdrant = None
        if QdrantClient is not None:
            self.qdrant = QdrantClient(**_qdrant_client_kwargs())

    async def trigger_ingestion(self, request: IngestRequest) -> IngestResponse:
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        if not request.file_url:
            return IngestResponse(
                task_id=task_id,
                status="FAILED",
                message="file_url is required for MVP ingestion",
                document_id=request.document_id,
            )

        started_at = _now()
        document_id = request.document_id or f"doc_{uuid.uuid4().hex[:12]}"
        document_row = self._upsert_processing_document(document_id, request, started_at)
        job_row = self._create_job(task_id, document_id, request.file_url, started_at)
        self._commit()

        try:
            raw_bytes = await self._load_file(request.file_url)
            text = self._extract_text(raw_bytes, request.file_url, request.document_type)
            chunks = self._chunk_text(text)
            self._upsert_chunks(document_row, chunks)

            finished_at = _now()
            document_row.chunks_count = len(chunks)
            document_row.ingestion_status = "done"
            document_row.updated_at = finished_at
            job_row.status = "done"
            job_row.message = "Document indexed successfully"
            job_row.chunks_indexed = len(chunks)
            job_row.error = None
            job_row.finished_at = finished_at
        except Exception as exc:
            finished_at = _now()
            document_row.ingestion_status = "failed"
            document_row.updated_at = finished_at
            job_row.status = "failed"
            job_row.message = "Document ingestion failed"
            job_row.error = str(exc)
            job_row.finished_at = finished_at

        self._commit()
        return IngestResponse(
            task_id=task_id,
            status=job_row.status.upper(),
            message=job_row.error or job_row.message,
            document_id=document_row.document_id,
            chunks_indexed=job_row.chunks_indexed,
        )

    async def retry_job(self, task_id: str) -> Optional[IngestResponse]:
        if self.db is None:
            return None
        job = self.db.query(IngestionJobRecord).filter(IngestionJobRecord.task_id == task_id).first()
        if not job:
            return None
        document = self.db.query(DocumentRecordModel).filter(DocumentRecordModel.document_id == job.document_id).first()
        metadata = {}
        if document:
            metadata = {
                "title": document.title,
                "domain": document.domain,
                "effective_status": document.effective_status,
            }
        return await self.trigger_ingestion(
            IngestRequest(
                file_url=job.file_url,
                document_id=job.document_id,
                document_type=document.document_type if document else "PDF",
                metadata=metadata,
            )
        )

    async def trigger_pubsub_ingestion(self, envelope: PubSubPushEnvelope) -> IngestResponse:
        event = self._decode_uploaded_event(envelope)
        response = await self.trigger_ingestion(
            IngestRequest(
                file_url=event.gcsUrl,
                document_id=event.documentId,
                document_type=event.documentType or "PDF",
                metadata={"title": event.originalFileName},
            )
        )
        if response.status.upper() == "FAILED":
            raise RuntimeError(response.message)
        return response

    def list_jobs(self) -> List[IngestionJob]:
        if self.db is None:
            return []
        rows = (
            self.db.query(IngestionJobRecord)
            .order_by(IngestionJobRecord.started_at.desc())
            .all()
        )
        return [self._job_to_schema(row) for row in rows]

    def list_documents(self) -> List[DocumentRecord]:
        if self.db is None:
            return []
        rows = (
            self.db.query(DocumentRecordModel)
            .order_by(DocumentRecordModel.updated_at.desc())
            .all()
        )
        return [self._document_to_schema(row) for row in rows]

    def disable_document(self, document_id: str) -> Optional[DocumentRecord]:
        return self._set_document_enabled(document_id, False)

    def enable_document(self, document_id: str) -> Optional[DocumentRecord]:
        return self._set_document_enabled(document_id, True)

    def admin_stats(self) -> dict:
        if self.db is None:
            return {
                "documents_total": 0,
                "chunks_total": 0,
                "jobs_failed": 0,
                "jobs_processing": 0,
                "service_status": "ok",
            }
        chunks_total = self.db.query(func.coalesce(func.sum(DocumentRecordModel.chunks_count), 0)).scalar() or 0
        jobs_failed = self.db.query(IngestionJobRecord).filter(IngestionJobRecord.status == "failed").count()
        jobs_processing = (
            self.db.query(IngestionJobRecord)
            .filter(IngestionJobRecord.status.in_(("queued", "processing")))
            .count()
        )
        return {
            "documents_total": self.db.query(DocumentRecordModel).count(),
            "chunks_total": int(chunks_total),
            "jobs_failed": jobs_failed,
            "jobs_processing": jobs_processing,
            "service_status": "ok",
        }

    async def _load_file(self, file_url: str) -> bytes:
        parsed = urlparse(file_url)
        if parsed.scheme in {"http", "https"}:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                return response.content
        if parsed.scheme == "gs":
            if storage is None:
                raise RuntimeError("google-cloud-storage is not installed")
            client = storage.Client(project=settings.GCP_PROJECT_ID)
            bucket = client.bucket(parsed.netloc)
            blob = bucket.blob(parsed.path.lstrip("/"))
            return blob.download_as_bytes()
        if parsed.scheme == "file":
            with open(parsed.path, "rb") as handle:
                return handle.read()
        with open(file_url, "rb") as handle:
            return handle.read()

    def _extract_text(self, raw_bytes: bytes, file_url: str, document_type: str) -> str:
        looks_like_pdf = document_type.upper() == "PDF" or file_url.lower().endswith(".pdf")
        if looks_like_pdf:
            if pdfplumber is None:
                raise RuntimeError("pdfplumber is not installed")
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n\n".join(page for page in pages if page.strip())
        else:
            text = raw_bytes.decode("utf-8", errors="ignore")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            raise RuntimeError("No extractable text found")
        return text

    def _chunk_text(self, text: str) -> List[str]:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
        chunks: List[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= settings.CHUNK_SIZE:
                current = f"{current}\n\n{paragraph}".strip()
            else:
                if current:
                    chunks.append(current)
                if len(paragraph) <= settings.CHUNK_SIZE:
                    current = paragraph
                else:
                    step = max(settings.CHUNK_SIZE - settings.CHUNK_OVERLAP, 1)
                    for start in range(0, len(paragraph), step):
                        chunks.append(paragraph[start : start + settings.CHUNK_SIZE])
                    current = ""
        if current:
            chunks.append(current)
        return chunks

    def _upsert_chunks(self, document: DocumentRecordModel, chunks: List[str]) -> None:
        if self.qdrant is None:
            return
        ensure_sparse_collection_schema(self.qdrant)
        vectors = self._embed_chunks(chunks)
        prepared_chunks = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            article_match = re.search(r"(Điều\s+\d+[^\n.]*)", chunk, flags=re.IGNORECASE)
            article = article_match.group(1) if article_match else ""
            prepared_chunks.append(
                {
                    "index": index,
                    "chunk": chunk,
                    "vector": vector,
                    "article": article,
                    "sparse_text": build_sparse_text(document.title, article, chunk),
                }
            )
        avg_len = estimate_bm25_avg_len([item["sparse_text"] for item in prepared_chunks])
        points = []
        for item in prepared_chunks:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document.document_id}:{item['index']}"))
            points.append(
                PointStruct(
                    id=point_id,
                    vector={
                        "": item["vector"],
                        sparse_vector_name(): build_bm25_document(item["sparse_text"], avg_len),
                    },
                    payload={
                        "document_id": document.document_id,
                        "title": document.title,
                        "source_url": document.source_url,
                        "domain": document.domain,
                        "article": item["article"],
                        "chunk_index": item["index"],
                        "effective_status": document.effective_status,
                        "content": item["chunk"],
                        "enabled": document.enabled,
                    },
                )
            )
        if points:
            self.qdrant.upsert(collection_name=settings.COLLECTION_NAME, points=points)

    def _embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        if not chunks:
            return []
        batch_size = max(settings.VERTEX_EMBEDDING_BATCH_SIZE, 1)
        try:
            vectors: List[List[float]] = []
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                vectors.extend(VERTEX_EMBEDDINGS.embed_texts(batch))
            if len(vectors) == len(chunks):
                return vectors
        except Exception:
            pass
        return [_embedding(chunk) for chunk in chunks]

    def _upsert_processing_document(
        self,
        document_id: str,
        request: IngestRequest,
        started_at: datetime,
    ) -> DocumentRecordModel:
        metadata = request.metadata or {}
        if self.db is None:
            raise RuntimeError("Database session is not available")
        row = self.db.query(DocumentRecordModel).filter(DocumentRecordModel.document_id == document_id).first()
        if row is None:
            row = DocumentRecordModel(
                document_id=document_id,
                title=_title_from_request(request),
                source_url=request.file_url or "",
                document_type=request.document_type,
                domain=str(metadata.get("domain", "general")),
                effective_status=str(metadata.get("effective_status", "unknown")),
                enabled=True,
                chunks_count=0,
                ingestion_status="processing",
                created_at=started_at,
                updated_at=started_at,
            )
            self.db.add(row)
            return row

        row.title = _title_from_request(request)
        row.source_url = request.file_url or row.source_url
        row.document_type = request.document_type or row.document_type
        row.domain = str(metadata.get("domain", row.domain or "general"))
        row.effective_status = str(metadata.get("effective_status", row.effective_status or "unknown"))
        row.ingestion_status = "processing"
        row.updated_at = started_at
        return row

    def _create_job(
        self,
        task_id: str,
        document_id: str,
        file_url: str,
        started_at: datetime,
    ) -> IngestionJobRecord:
        if self.db is None:
            raise RuntimeError("Database session is not available")
        row = IngestionJobRecord(
            task_id=task_id,
            document_id=document_id,
            status="processing",
            file_url=file_url,
            message="Ingestion started",
            chunks_indexed=0,
            started_at=started_at,
        )
        self.db.add(row)
        return row

    def _set_document_enabled(self, document_id: str, enabled: bool) -> Optional[DocumentRecord]:
        if self.db is None:
            return None
        row = self.db.query(DocumentRecordModel).filter(DocumentRecordModel.document_id == document_id).first()
        if row is None:
            return None
        row.enabled = enabled
        row.updated_at = _now()
        self._sync_enabled_payload(document_id, enabled)
        self._commit()
        return self._document_to_schema(row)

    def _sync_enabled_payload(self, document_id: str, enabled: bool) -> None:
        if self.qdrant is None or Filter is None or FieldCondition is None or MatchValue is None:
            return
        try:
            self.qdrant.set_payload(
                collection_name=settings.COLLECTION_NAME,
                payload={"enabled": enabled},
                points=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]),
            )
        except Exception:
            return

    def _commit(self) -> None:
        if self.db is None:
            return
        self.db.commit()

    @staticmethod
    def _decode_uploaded_event(envelope: PubSubPushEnvelope) -> DocumentUploadedEvent:
        try:
            payload = b64decode(envelope.message.data).decode("utf-8")
            return DocumentUploadedEvent.model_validate(json.loads(payload))
        except Exception as exc:
            raise RuntimeError("Invalid Pub/Sub upload event payload") from exc

    @staticmethod
    def _document_to_schema(row: DocumentRecordModel) -> DocumentRecord:
        return DocumentRecord(
            document_id=row.document_id,
            title=row.title,
            source_url=row.source_url,
            document_type=row.document_type,
            domain=row.domain,
            effective_status=row.effective_status,
            enabled=row.enabled,
            chunks_count=row.chunks_count,
            ingestion_status=row.ingestion_status,
            created_at=_iso(row.created_at),
            updated_at=_iso(row.updated_at),
        )

    @staticmethod
    def _job_to_schema(row: IngestionJobRecord) -> IngestionJob:
        return IngestionJob(
            task_id=row.task_id,
            document_id=row.document_id,
            status=row.status,
            file_url=row.file_url,
            message=row.message,
            chunks_indexed=row.chunks_indexed,
            error=row.error,
            started_at=_iso(row.started_at),
            finished_at=_iso(row.finished_at) or None,
        )
