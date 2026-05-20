#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-legal-chatbot-496302}"
REGION="${REGION:-asia-southeast1}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-legal-chatbot-496302:asia-southeast1:legal-rag-db-prod}"
COLLECTION_NAME="${COLLECTION_NAME:-legal_documents_prod}"
DB_NAME="${DB_NAME:-metadata_db}"
DB_USER="${DB_USER:-legal_app_user}"
DB_PROXY_HOST="${DB_PROXY_HOST:-host.docker.internal}"
DB_PROXY_PORT="${DB_PROXY_PORT:-5433}"
QDRANT_SPARSE_VECTOR_NAME="${QDRANT_SPARSE_VECTOR_NAME:-bm25_sparse_vector}"
BM25_AVG_LEN="${BM25_AVG_LEN:-0}"
BM25_LANGUAGE="${BM25_LANGUAGE:-none}"
BM25_TOKENIZER="${BM25_TOKENIZER:-multilingual}"
BM25_ASCII_FOLDING="${BM25_ASCII_FOLDING:-true}"
IMPORT_LIMIT="${1:-20}"
BATCH_SIZE="${BATCH_SIZE:-8}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-2}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [limit]

Imports Hugging Face legal documents from your local machine into:
  - Qdrant production collection: ${COLLECTION_NAME}
  - Cloud SQL production database: ${DB_NAME}

Environment overrides:
  PROJECT_ID
  REGION
  CLOUD_SQL_INSTANCE
  COLLECTION_NAME
  DB_NAME
  DB_USER
  DB_PROXY_HOST
  DB_PROXY_PORT
  QDRANT_SPARSE_VECTOR_NAME
  BM25_AVG_LEN
  BM25_LANGUAGE
  BM25_TOKENIZER
  BM25_ASCII_FOLDING
  BATCH_SIZE
  EMBEDDING_BATCH_SIZE

Examples:
  $(basename "$0")
  $(basename "$0") 20
  BATCH_SIZE=4 EMBEDDING_BATCH_SIZE=1 $(basename "$0") 50
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

if [[ "${IMPORT_LIMIT}" == "-h" || "${IMPORT_LIMIT}" == "--help" ]]; then
  usage
  exit 0
fi

if ! [[ "${IMPORT_LIMIT}" =~ ^[0-9]+$ ]]; then
  echo "Limit must be a non-negative integer. Got: ${IMPORT_LIMIT}" >&2
  exit 1
fi

require_command gcloud
require_command docker

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running or not reachable." >&2
  exit 1
fi

if ! gcloud config get-value project >/dev/null 2>&1; then
  echo "gcloud is not configured. Run 'gcloud auth login' and 'gcloud config set project ${PROJECT_ID}' first." >&2
  exit 1
fi

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
  echo "Active gcloud project is '${ACTIVE_PROJECT}', expected '${PROJECT_ID}'." >&2
  echo "Run: gcloud config set project ${PROJECT_ID}" >&2
  exit 1
fi

echo "Checking Cloud SQL proxy on ${DB_PROXY_HOST}:${DB_PROXY_PORT}..."
if ! docker run --rm alpine:3.20 sh -c "apk add --no-cache netcat-openbsd >/dev/null && nc -z ${DB_PROXY_HOST} ${DB_PROXY_PORT}" >/dev/null 2>&1; then
  cat >&2 <<EOF
Cloud SQL proxy does not appear to be reachable at ${DB_PROXY_HOST}:${DB_PROXY_PORT}.

Start it in another terminal, for example:
  cloud-sql-proxy ${CLOUD_SQL_INSTANCE} --port ${DB_PROXY_PORT}

Or with Docker:
  docker run --rm -it -p ${DB_PROXY_PORT}:5432 gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.18.2 --address 0.0.0.0 ${CLOUD_SQL_INSTANCE}
EOF
  exit 1
fi

echo "Fetching production secrets from Secret Manager..."
PROD_DB_PASSWORD="$(gcloud secrets versions access latest --secret=legal-rag-db-password-prod)"
PROD_QDRANT_URL="$(gcloud secrets versions access latest --secret=qdrant-url-prod)"
PROD_QDRANT_API_KEY="$(gcloud secrets versions access latest --secret=qdrant-api-key-prod)"

DATABASE_URL="postgresql://${DB_USER}:${PROD_DB_PASSWORD}@${DB_PROXY_HOST}:${DB_PROXY_PORT}/${DB_NAME}"

echo "Starting production import:"
echo "  Project: ${PROJECT_ID}"
echo "  Region: ${REGION}"
echo "  Collection: ${COLLECTION_NAME}"
echo "  Sparse vector: ${QDRANT_SPARSE_VECTOR_NAME}"
echo "  Limit: ${IMPORT_LIMIT}"
echo "  Batch size: ${BATCH_SIZE}"
echo "  Embedding batch size: ${EMBEDDING_BATCH_SIZE}"

docker compose run --rm \
  -e QDRANT_URL="${PROD_QDRANT_URL}" \
  -e QDRANT_API_KEY="${PROD_QDRANT_API_KEY}" \
  -e COLLECTION_NAME="${COLLECTION_NAME}" \
  -e DATABASE_URL="${DATABASE_URL}" \
  -e GCP_PROJECT_ID="${PROJECT_ID}" \
  -e GCP_LOCATION="${REGION}" \
  -e QDRANT_SPARSE_VECTOR_NAME="${QDRANT_SPARSE_VECTOR_NAME}" \
  -e BM25_AVG_LEN="${BM25_AVG_LEN}" \
  -e BM25_LANGUAGE="${BM25_LANGUAGE}" \
  -e BM25_TOKENIZER="${BM25_TOKENIZER}" \
  -e BM25_ASCII_FOLDING="${BM25_ASCII_FOLDING}" \
  -e PYTHONUNBUFFERED="1" \
  ingestion-service \
  python -u scripts/import_hf_legal_documents.py \
    --limit "${IMPORT_LIMIT}" \
    --batch-size "${BATCH_SIZE}" \
    --embedding-batch-size "${EMBEDDING_BATCH_SIZE}"
