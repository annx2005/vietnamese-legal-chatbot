import argparse
import hashlib
import os
import sys
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence

from datasets import load_dataset
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.models import Base, DocumentRecordModel, IngestionJobRecord
from app.db.session import SessionLocal, engine
from app.services.qdrant_sparse import (
    build_bm25_document,
    build_sparse_text,
    ensure_sparse_collection_schema,
    estimate_bm25_avg_len,
    sparse_vector_name,
)
from app.services.vertex_ai_service import VertexAIEmbeddingService


DATASET_NAME = "vohuutridung/vietnamese-legal-documents"
DEFAULT_IMPORT_LIMIT = 10

DOMAIN_KEYWORDS = {
    "dan-su": ("dan su", "hop dong", "nghia vu", "quyen dan su", "bo luat dan su"),
    "dat-dai": ("dat dai", "nha dat", "bat dong san", "quyen su dung dat"),
    "lao-dong": ("lao dong", "viec lam", "tien luong", "bao hiem xa hoi", "hop dong lao dong"),
}

VERTEX_EMBEDDINGS = VertexAIEmbeddingService()
VERTEX_EMBEDDINGS_AVAILABLE = True


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.lower()


def create_embedding(text: str) -> List[float]:
    vector = [0.0] * settings.VECTOR_SIZE
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % settings.VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]


def create_embeddings(texts: Sequence[str], allow_local_fallback: bool) -> List[List[float]]:
    global VERTEX_EMBEDDINGS_AVAILABLE

    if not VERTEX_EMBEDDINGS_AVAILABLE:
        return [create_embedding(text) for text in texts]

    try:
        vectors = VERTEX_EMBEDDINGS.embed_texts(list(texts))
        if len(vectors) == len(texts):
            return vectors
    except Exception as exc:
        if not allow_local_fallback:
            raise RuntimeError("Vertex embedding failed. Re-run with --allow-local-embedding-fallback to import offline.") from exc
        VERTEX_EMBEDDINGS_AVAILABLE = False
        print(f"Vertex embedding failed, falling back to local embeddings: {exc}", file=sys.stderr)
    return [create_embedding(text) for text in texts]


def iter_chunks(text: str, chunk_size: int, chunk_overlap: int) -> Iterator[str]:
    normalized = re.sub(r"[ \t]+", " ", text)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
            continue

        if current:
            yield current
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        step = max(chunk_size - chunk_overlap, 1)
        for start in range(0, len(paragraph), step):
            yield paragraph[start : start + chunk_size]
        current = ""

    if current:
        yield current


def matches_domains(metadata: dict, domains: Sequence[str]) -> bool:
    if not domains:
        return True
    searchable = normalize_text(
        " ".join(
            [
                metadata.get("title", ""),
                metadata.get("legal_type", ""),
                metadata.get("legal_sectors", ""),
            ]
        )
    )
    for domain in domains:
        keywords = DOMAIN_KEYWORDS.get(domain, (normalize_text(domain),))
        if any(keyword in searchable for keyword in keywords):
            return True
    return False


def select_metadata(limit: int | None, domains: Sequence[str]) -> Dict[int, dict]:
    selected: Dict[int, dict] = {}
    metadata_rows = load_dataset(DATASET_NAME, "metadata", split="data", streaming=True)
    for row in metadata_rows:
        if not matches_domains(row, domains):
            continue
        document_id = int(row["id"])
        selected[document_id] = {
            "id": document_id,
            "title": row.get("title") or f"Legal document {document_id}",
            "url": row.get("url") or "",
            "legal_type": row.get("legal_type") or "",
            "legal_sectors": row.get("legal_sectors") or "",
            "issuing_authority": row.get("issuing_authority") or "",
            "issuance_date": row.get("issuance_date") or "",
        }
        if limit is not None and len(selected) >= limit:
            break
    return selected


def qdrant_client_kwargs() -> dict:
    kwargs = {}
    if settings.QDRANT_URL:
        kwargs["url"] = settings.QDRANT_URL
    else:
        kwargs["host"] = settings.QDRANT_HOST
        kwargs["port"] = settings.QDRANT_PORT
    if settings.QDRANT_API_KEY:
        kwargs["api_key"] = settings.QDRANT_API_KEY
    return kwargs


def batched(items: Iterable[PointStruct], batch_size: int) -> Iterable[List[PointStruct]]:
    batch: List[PointStruct] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def batched_texts(items: Iterable[str], batch_size: int) -> Iterable[List[str]]:
    batch: List[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def make_document_points(
    document_id: int,
    metadata: dict,
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_batch_size: int,
    allow_local_fallback: bool,
) -> Iterable[PointStruct]:
    chunk_count = 0
    batch_size = max(embedding_batch_size, 1)
    print(f"Processing document {document_id}: {metadata['title'][:120]}", flush=True)
    chunks = list(iter_chunks(text, chunk_size, chunk_overlap))
    articles = []
    sparse_texts = []
    for chunk in chunks:
        article_match = re.search(r"(Điều\s+\d+[^\n.]*)", chunk, flags=re.IGNORECASE)
        article = article_match.group(1) if article_match else ""
        articles.append(article)
        sparse_texts.append(build_sparse_text(metadata["title"], article, chunk))
    avg_len = estimate_bm25_avg_len(sparse_texts)

    for start in range(0, len(chunks), batch_size):
        batch_chunks = chunks[start : start + batch_size]
        vectors = create_embeddings(batch_chunks, allow_local_fallback)
        batch_articles = articles[start : start + batch_size]
        batch_sparse_texts = sparse_texts[start : start + batch_size]
        for chunk, vector, article, sparse_text in zip(batch_chunks, vectors, batch_articles, batch_sparse_texts):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"hf:{document_id}:{chunk_count}"))
            yield PointStruct(
                id=point_id,
                vector={
                    "": vector,
                    sparse_vector_name(): build_bm25_document(sparse_text, avg_len),
                },
                payload={
                    "id": document_id,
                    "document_id": str(document_id),
                    "hf_id": document_id,
                    "title": metadata["title"],
                    "source_url": metadata["url"],
                    "url": metadata["url"],
                    "legal_type": metadata["legal_type"],
                    "legal_sectors": metadata["legal_sectors"],
                    "domain": metadata["legal_sectors"],
                    "issuing_authority": metadata["issuing_authority"],
                    "issuance_date": metadata["issuance_date"],
                    "effective_status": "unknown",
                    "article": article,
                    "chunk_index": chunk_count,
                    "content": chunk,
                    "enabled": True,
                    "source": DATASET_NAME,
                    "embedding_model": settings.EMBEDDING_MODEL_NAME,
                    "embedding_provider": "vertex-ai" if not allow_local_fallback else "vertex-ai-or-local-fallback",
                },
            )
            chunk_count += 1
    print(f"Finished document {document_id} with {chunk_count} chunks", flush=True)


def make_points(
    metadata_by_id: Dict[int, dict],
    chunk_size: int,
    chunk_overlap: int,
    embedding_batch_size: int,
    allow_local_fallback: bool,
) -> Iterable[PointStruct]:
    remaining = set(metadata_by_id.keys())
    content_rows = load_dataset(DATASET_NAME, "content", split="data", streaming=True)
    for row in content_rows:
        document_id = int(row["id"])
        if document_id not in remaining:
            continue

        metadata = metadata_by_id[document_id]
        yield from make_document_points(
            document_id=document_id,
            metadata=metadata,
            text=str(row.get("content") or ""),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_batch_size=embedding_batch_size,
            allow_local_fallback=allow_local_fallback,
        )

        remaining.remove(document_id)
        if not remaining:
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a small Hugging Face legal corpus sample into Qdrant.")
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("HF_IMPORT_LIMIT", str(DEFAULT_IMPORT_LIMIT))),
        help="Number of documents to import. Use 0 for the full dataset.",
    )
    parser.add_argument(
        "--domains",
        default="",
        help="Comma-separated domain filters. Default imports all domains; example: dan-su,dat-dai,lao-dong.",
    )
    parser.add_argument("--batch-size", type=int, default=64, help="Qdrant upsert batch size.")
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=settings.VERTEX_EMBEDDING_BATCH_SIZE,
        help="Vertex AI embedding batch size.",
    )
    parser.add_argument("--chunk-size", type=int, default=settings.CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=settings.CHUNK_OVERLAP)
    parser.add_argument(
        "--allow-local-embedding-fallback",
        action="store_true",
        help="Import with local deterministic embeddings if Vertex AI is unavailable. Use only for offline demos.",
    )
    return parser.parse_args()


def persist_import_state(metadata_by_id: Dict[int, dict], chunk_counts: Dict[str, int]) -> None:
    finished_at = datetime.now(timezone.utc)
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
    except Exception as exc:
        print(f"Warning: could not initialize PostgreSQL persistence for HF import: {exc}", file=sys.stderr)
        return

    try:
        for raw_document_id, metadata in metadata_by_id.items():
            document_id = str(raw_document_id)
            source_url = metadata["url"] or f"hf://{DATASET_NAME}/{document_id}"
            row = (
                db.query(DocumentRecordModel)
                .filter(DocumentRecordModel.document_id == document_id)
                .first()
            )
            if row is None:
                row = DocumentRecordModel(
                    document_id=document_id,
                    title=metadata["title"],
                    source_url=source_url,
                    document_type="TEXT",
                    domain=metadata["legal_sectors"] or "general",
                    effective_status="unknown",
                    enabled=True,
                    created_at=finished_at,
                    updated_at=finished_at,
                )
                db.add(row)
            row.title = metadata["title"]
            row.source_url = source_url
            row.document_type = "TEXT"
            row.domain = metadata["legal_sectors"] or "general"
            row.effective_status = "unknown"
            row.enabled = True
            row.chunks_count = chunk_counts.get(document_id, 0)
            row.ingestion_status = "done"
            row.updated_at = finished_at

            task_id = f"hf_import_{document_id}"
            job = (
                db.query(IngestionJobRecord)
                .filter(IngestionJobRecord.task_id == task_id)
                .first()
            )
            if job is None:
                job = IngestionJobRecord(
                    task_id=task_id,
                    document_id=document_id,
                    status="done",
                    file_url=source_url,
                    message="Imported from Hugging Face dataset",
                    started_at=finished_at,
                    finished_at=finished_at,
                )
                db.add(job)
            job.document_id = document_id
            job.status = "done"
            job.file_url = source_url
            job.message = "Imported from Hugging Face dataset"
            job.chunks_indexed = chunk_counts.get(document_id, 0)
            job.error = None
            job.finished_at = finished_at

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Warning: failed to persist imported document metadata to PostgreSQL: {exc}", file=sys.stderr)
    finally:
        db.close()


def main() -> None:
    args = parse_args()
    if args.limit < 0:
        raise ValueError("--limit must be greater than or equal to 0")

    domains = [domain.strip() for domain in args.domains.split(",") if domain.strip()]
    effective_limit = None if args.limit == 0 else args.limit
    limit_label = "all matching documents" if effective_limit is None else f"up to {effective_limit} documents"
    print(f"Selecting {limit_label} from {DATASET_NAME} for domains: {domains or 'all'}", flush=True)
    metadata_by_id = select_metadata(effective_limit, domains)
    if not metadata_by_id:
        raise RuntimeError("No matching metadata rows found. Try a larger --limit or verify dataset access.")
    print(f"Selected {len(metadata_by_id)} metadata rows", flush=True)

    client = QdrantClient(**qdrant_client_kwargs())
    ensure_sparse_collection_schema(client)

    total_points = 0
    chunk_counts: Dict[str, int] = {}
    points = make_points(
        metadata_by_id,
        args.chunk_size,
        args.chunk_overlap,
        max(args.embedding_batch_size, 1),
        args.allow_local_embedding_fallback,
    )
    for batch in batched(points, args.batch_size):
        client.upsert(collection_name=settings.COLLECTION_NAME, points=batch)
        for point in batch:
            document_id = str((point.payload or {}).get("document_id", ""))
            if document_id:
                chunk_counts[document_id] = chunk_counts.get(document_id, 0) + 1
        total_points += len(batch)
        print(f"Upserted {total_points} chunks...", flush=True)

    persist_import_state(metadata_by_id, chunk_counts)

    print(
        f"Imported {len(metadata_by_id)} documents and {total_points} chunks "
        f"into Qdrant collection '{settings.COLLECTION_NAME}'.",
        flush=True,
    )


if __name__ == "__main__":
    main()
