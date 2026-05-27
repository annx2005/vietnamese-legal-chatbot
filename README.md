# Vietnamese Legal RAG Chatbot 

A Microservice Vietnamese legal chatbot with public chat, admin document ingestion, RAG citations, and reviewable chat logs.

## Services

- `frontend`: Vite + React app with `/chat` and `/admin`.
- `api-router`: Nginx reverse proxy entrypoint for `/api/v1/*` in both local and Cloud Run.
- `upload-service`: uploads PDF files to GCS and returns document metadata.
- `ingestion-service`: reads PDF/text, chunks content, creates Vertex AI dense embeddings plus Qdrant BM25 sparse vectors, and upserts both into Qdrant.
- `rag-service`: retrieves legal chunks from Qdrant with native hybrid search, calls Gemini to draft grounded answers, and returns citations with confidence fallback.
- `postgres`, `qdrant`: local infrastructure.

## Run Local

```bash
docker compose up --build
```

Open:

- Chat: `http://localhost:5173/chat`
- Admin: `http://localhost:5173/admin`
- API Router: `http://localhost:8080`
- RAG docs: `http://localhost:8000/docs`
- Ingestion docs: `http://localhost:8001/docs`

## Flow

1. Admin logs in at `/admin` and receives a Bearer JWT.
2. Admin uploads a PDF or submits a file URL in `/admin`.
3. `upload-service` stores PDFs in GCS when credentials are configured.
4. `ingestion-service` extracts text, chunks it, and writes dense + sparse vectors to Qdrant.
5. User asks a question in `/chat`.
6. `rag-service` retrieves relevant chunks with Qdrant native hybrid search and returns an answer with citations.
7. Admin reviews answers in `Chat Logs`.

Admin upload, ingestion, and review APIs require a JWT with `ROLE_ADMIN`. Local defaults are `ADMIN_USERNAME=admin` and `ADMIN_PASSWORD=admin123`; change `JWT_SECRET_KEY` before any shared demo or deployment.

Local Docker uses the cloud Qdrant endpoint from `.env`, but keeps its vectors in `COLLECTION_NAME=legal_documents_local` so they stay isolated from production.

For easiest local testing without GCS, use the admin `file URL` field with a local text or PDF path that is visible inside the `ingestion-service` container, or call `POST /api/v1/ingest/` directly with an accessible `http`, `file`, `gs`, or container-local path.

## Import Hugging Face Legal Dataset

The ingestion service includes a small importer for `vohuutridung/vietnamese-legal-documents`. It chunks the text, upserts vectors into the configured Qdrant collection, and persists matching metadata rows into PostgreSQL `documents` and `ingestion_jobs`.

If `QDRANT_URL` is set, the importer and runtime services connect to Qdrant Cloud using `QDRANT_API_KEY`. Otherwise they fall back to local `QDRANT_HOST` and `QDRANT_PORT`.

To import directly into Qdrant Cloud from local Docker, set these in `.env` first:

```bash
QDRANT_URL=https://your-cluster-endpoint
QDRANT_API_KEY=your-qdrant-api-key
```

Rebuild the ingestion image after dependency changes:

```bash
docker compose up -d --build ingestion-service
```

Import a small local demo sample:

```bash
docker compose exec ingestion-service python scripts/import_hf_legal_documents.py
```

By default the importer reads `HF_IMPORT_LIMIT` from the environment. The checked-in local `.env` uses `HF_IMPORT_LIMIT=10`, so the command above imports 10 documents into `legal_documents_local`.

To override the local limit manually:

```bash
docker compose exec ingestion-service python scripts/import_hf_legal_documents.py --limit 25
```

To import the full dataset into production, run the manual GitHub Actions workflow `Import Production Dataset`. It creates or updates a Cloud Run Job that uses the production `ingestion-service` image and config, writes vectors into `legal_documents_prod`, and persists metadata into Cloud SQL `metadata_db`.

Useful options:

```bash
--limit 200              # keep demo imports small; 200-1000 is enough for class demos
--domains dan-su,dat-dai # optionally restrict imports to selected legal domains
--batch-size 64          # Qdrant upsert batch size
```

The importer stores these metadata fields in each Qdrant payload: `id`, `title`, `url`, `legal_type`, `legal_sectors`, `issuing_authority`, and `issuance_date`.

## CI/CD for IaC

Terraform and Helm changes are validated in GitHub Actions on pull requests via the `IaC Checks` workflow. Pushes to `main` automatically run `terraform apply` before the GKE deploy when files under `terraform/**` change.

Configure a GitHub `prod` environment with these non-secret variables so Terraform does not rely on a checked-in `terraform.tfvars`:

```bash
TF_VAR_PROJECT_ID=legal-chatbot-496302
TF_VAR_REGION=asia-southeast1
TF_VAR_ENVIRONMENT=prod
TF_VAR_BUCKET_NAME=vietnamese-legal-rag-documents
TF_VAR_GITHUB_REPO=annx2005/vietnamese-legal-chatbot
```

## Notes

- The services now use Vertex AI for embeddings and answer generation when credentials are available.
- If Vertex AI is unavailable, the backend falls back to deterministic local embeddings and a template answer so local development still works.
- `rag-service` now defaults to `SEARCH_MODE=hybrid`, using Qdrant native hybrid retrieval with dense semantic prefetch + BM25 sparse prefetch fused by RRF. Set `SEARCH_MODE=semantic` to keep vector-only retrieval.
- BM25 sparse vectors are stored under `QDRANT_SPARSE_VECTOR_NAME=bm25_sparse_vector` by default and use `BM25_LANGUAGE=none`, `BM25_TOKENIZER=multilingual`, and `BM25_ASCII_FOLDING=true` so Vietnamese queries/chunks are normalized consistently.
- `BM25_AVG_LEN=0` means the ingestion pipeline estimates average token length from each ingest batch. For more stable ranking across incremental ingests, you can set a corpus-wide average explicitly.
- Existing points that were indexed before this change need to be re-ingested or backfilled once so they also receive sparse vectors. Use `docker compose exec ingestion-service python scripts/backfill_qdrant_sparse_vectors.py` for local backfill.
- Hybrid tuning envs for `rag-service`: `HYBRID_DENSE_PREFETCH_MULTIPLIER` and `HYBRID_SPARSE_PREFETCH_MULTIPLIER`.
- Prompt files live in `rag-service/app/prompts/system_prompt.txt` and `rag-service/app/prompts/user_prompt.txt`.
- Chat history, ingestion jobs, and document registry are in memory for this first version.
- The bot is designed for legal lookup with citations, not personalized legal advice.
