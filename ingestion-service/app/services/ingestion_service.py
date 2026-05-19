import hashlib
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from app.core.config import settings
from app.schemas.ingest import DocumentRecord, IngestRequest, IngestResponse, IngestionJob
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
    from qdrant_client.http.models import Distance, PointStruct, VectorParams
except ImportError:  # pragma: no cover - dependency is present in the image
    QdrantClient = None
    Distance = None
    PointStruct = None
    VectorParams = None


DOCUMENTS: Dict[str, DocumentRecord] = {}
JOBS: Dict[str, IngestionJob] = {}
VERTEX_EMBEDDINGS = VertexAIEmbeddingService()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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

class IngestionService:
    def __init__(self):
        self.qdrant = None
        if QdrantClient is not None:
            kwargs = {"host": settings.QDRANT_HOST, "port": settings.QDRANT_PORT}
            if settings.QDRANT_API_KEY:
                kwargs["api_key"] = settings.QDRANT_API_KEY
            self.qdrant = QdrantClient(**kwargs)

    async def trigger_ingestion(self, request: IngestRequest) -> IngestResponse:
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        if not request.file_url:
            return IngestResponse(
                task_id=task_id,
                status="FAILED",
                message="file_url is required for MVP ingestion",
                document_id=request.document_id,
            )

        document_id = request.document_id or f"doc_{uuid.uuid4().hex[:12]}"
        created_at = _now()
        document = DocumentRecord(
            document_id=document_id,
            title=_title_from_request(request),
            source_url=request.file_url,
            document_type=request.document_type,
            domain=str((request.metadata or {}).get("domain", "general")),
            effective_status=str((request.metadata or {}).get("effective_status", "unknown")),
            ingestion_status="processing",
            created_at=created_at,
            updated_at=created_at,
        )
        DOCUMENTS[document_id] = document

        job = IngestionJob(
            task_id=task_id,
            document_id=document_id,
            status="processing",
            file_url=request.file_url,
            message="Ingestion started",
            started_at=created_at,
        )
        JOBS[task_id] = job

        try:
            raw_bytes = await self._load_file(request.file_url)
            text = self._extract_text(raw_bytes, request.file_url, request.document_type)
            chunks = self._chunk_text(text)
            self._upsert_chunks(document, chunks)
            finished_at = _now()
            document.chunks_count = len(chunks)
            document.ingestion_status = "done"
            document.updated_at = finished_at
            job.status = "done"
            job.message = "Document indexed successfully"
            job.chunks_indexed = len(chunks)
            job.finished_at = finished_at
        except Exception as exc:
            finished_at = _now()
            document.ingestion_status = "failed"
            document.updated_at = finished_at
            job.status = "failed"
            job.message = "Document ingestion failed"
            job.error = str(exc)
            job.finished_at = finished_at

        return IngestResponse(
            task_id=task_id,
            status=job.status.upper(),
            message=job.error or job.message,
            document_id=document_id,
            chunks_indexed=job.chunks_indexed,
        )

    async def retry_job(self, task_id: str) -> Optional[IngestResponse]:
        job = JOBS.get(task_id)
        if not job:
            return None
        document = DOCUMENTS.get(job.document_id)
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

    def list_jobs(self) -> List[IngestionJob]:
        return sorted(JOBS.values(), key=lambda item: item.started_at, reverse=True)

    def list_documents(self) -> List[DocumentRecord]:
        return sorted(DOCUMENTS.values(), key=lambda item: item.updated_at, reverse=True)

    def disable_document(self, document_id: str) -> Optional[DocumentRecord]:
        document = DOCUMENTS.get(document_id)
        if document:
            document.enabled = False
            document.updated_at = _now()
        return document

    def enable_document(self, document_id: str) -> Optional[DocumentRecord]:
        document = DOCUMENTS.get(document_id)
        if document:
            document.enabled = True
            document.updated_at = _now()
        return document

    def admin_stats(self) -> dict:
        jobs = list(JOBS.values())
        return {
            "documents_total": len(DOCUMENTS),
            "chunks_total": sum(document.chunks_count for document in DOCUMENTS.values()),
            "jobs_failed": sum(1 for job in jobs if job.status == "failed"),
            "jobs_processing": sum(1 for job in jobs if job.status in {"queued", "processing"}),
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

    def _upsert_chunks(self, document: DocumentRecord, chunks: List[str]) -> None:
        if self.qdrant is None:
            return
        try:
            self.qdrant.get_collection(settings.COLLECTION_NAME)
        except Exception:
            self.qdrant.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config=VectorParams(size=settings.VECTOR_SIZE, distance=Distance.COSINE),
            )
        vectors = self._embed_chunks(chunks)
        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document.document_id}:{index}"))
            article_match = re.search(r"(Điều\s+\d+[^\n.]*)", chunk, flags=re.IGNORECASE)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document.document_id,
                        "title": document.title,
                        "source_url": document.source_url,
                        "domain": document.domain,
                        "article": article_match.group(1) if article_match else "",
                        "chunk_index": index,
                        "effective_status": document.effective_status,
                        "content": chunk,
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
