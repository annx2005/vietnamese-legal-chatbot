import re
from typing import Sequence

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    Document as QdrantDocument,
    Modifier,
    SparseVectorConfig,
    SparseVectorNameConfig,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import settings


def sparse_vector_name() -> str:
    return settings.QDRANT_SPARSE_VECTOR_NAME


def sparse_vector_params() -> SparseVectorParams:
    return SparseVectorParams(modifier=Modifier.IDF)


def sparse_vector_name_config() -> SparseVectorNameConfig:
    return SparseVectorNameConfig(
        sparse=SparseVectorConfig(modifier=Modifier.IDF),
    )


def collection_has_sparse_vector(collection_info) -> bool:
    params = getattr(getattr(collection_info, "config", None), "params", None)
    sparse_vectors = getattr(params, "sparse_vectors", None) or {}
    return sparse_vector_name() in sparse_vectors


def ensure_sparse_collection_schema(client: QdrantClient) -> None:
    try:
        collection_info = client.get_collection(settings.COLLECTION_NAME)
    except Exception:
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=VectorParams(size=settings.VECTOR_SIZE, distance=Distance.COSINE),
            sparse_vectors_config={sparse_vector_name(): sparse_vector_params()},
        )
        return

    if collection_has_sparse_vector(collection_info):
        return

    try:
        client.create_vector_name(
            collection_name=settings.COLLECTION_NAME,
            vector_name=sparse_vector_name(),
            vector_name_config=sparse_vector_name_config(),
        )
    except Exception:
        refreshed = client.get_collection(settings.COLLECTION_NAME)
        if not collection_has_sparse_vector(refreshed):
            raise


def build_sparse_text(title: str, article: str, content: str) -> str:
    return "\n".join(part.strip() for part in (title, article, content) if part and part.strip()).strip()


def estimate_bm25_avg_len(texts: Sequence[str]) -> float:
    if settings.BM25_AVG_LEN > 0:
        return float(settings.BM25_AVG_LEN)

    token_counts = [len(re.findall(r"\w+", text, flags=re.UNICODE)) for text in texts if text.strip()]
    if not token_counts:
        return 1.0
    return max(sum(token_counts) / len(token_counts), 1.0)


def build_bm25_document(text: str, avg_len: float) -> QdrantDocument:
    return QdrantDocument(
        text=text,
        model="qdrant/bm25",
        options={
            "avg_len": avg_len,
            "language": settings.BM25_LANGUAGE,
            "tokenizer": settings.BM25_TOKENIZER,
            "ascii_folding": settings.BM25_ASCII_FOLDING,
        },
    )
