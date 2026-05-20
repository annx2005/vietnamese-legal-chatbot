import argparse
import sys
from pathlib import Path
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointVectors

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.qdrant_sparse import (
    build_bm25_document,
    build_sparse_text,
    ensure_sparse_collection_schema,
    estimate_bm25_avg_len,
    sparse_vector_name,
)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill native BM25 sparse vectors into an existing Qdrant collection.")
    parser.add_argument("--batch-size", type=int, default=128, help="Number of points to update per batch.")
    return parser.parse_args()


def iter_records(client: QdrantClient):
    offset = None
    while True:
        records, offset = client.scroll(
            collection_name=settings.COLLECTION_NAME,
            offset=offset,
            limit=256,
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            break
        for record in records:
            yield record
        if offset is None:
            break


def main() -> None:
    args = parse_args()
    client = QdrantClient(**qdrant_client_kwargs())
    ensure_sparse_collection_schema(client)

    records = list(iter_records(client))
    if not records:
        print(f"No points found in collection '{settings.COLLECTION_NAME}'.", flush=True)
        return

    sparse_texts = []
    prepared = []
    for record in records:
        payload = record.payload or {}
        title = str(payload.get("title", ""))
        article = str(payload.get("article", ""))
        content = str(payload.get("content", ""))
        sparse_text = build_sparse_text(title, article, content)
        sparse_texts.append(sparse_text)
        prepared.append((record.id, sparse_text))

    avg_len = estimate_bm25_avg_len(sparse_texts)
    print(
        f"Backfilling {len(prepared)} points in '{settings.COLLECTION_NAME}' with avg_len={avg_len:.2f}.",
        flush=True,
    )

    updated = 0
    batch: List[PointVectors] = []
    for point_id, sparse_text in prepared:
        batch.append(
            PointVectors(
                id=point_id,
                vector={sparse_vector_name(): build_bm25_document(sparse_text, avg_len)},
            )
        )
        if len(batch) >= max(args.batch_size, 1):
            client.update_vectors(collection_name=settings.COLLECTION_NAME, points=batch, wait=True)
            updated += len(batch)
            print(f"Updated {updated} points...", flush=True)
            batch = []

    if batch:
        client.update_vectors(collection_name=settings.COLLECTION_NAME, points=batch, wait=True)
        updated += len(batch)

    print(f"Backfilled sparse vectors for {updated} points.", flush=True)


if __name__ == "__main__":
    main()
