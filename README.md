# Legal RAG Chatbot MVP

Microservice MVP for a Vietnamese legal chatbot with public chat, admin document ingestion, RAG citations, and reviewable chat logs.

## Services

- `frontend`: Vite + React app with `/chat` and `/admin`.
- `api-router`: Nginx reverse proxy entrypoint for `/api/v1/*` in both local and Cloud Run.
- `upload-service`: uploads PDF files to GCS and returns document metadata.
- `ingestion-service`: reads PDF/text, chunks content, creates Vertex AI embeddings, and upserts chunks into Qdrant.
- `rag-service`: retrieves legal chunks from Qdrant, calls Gemini to draft grounded answers, and returns citations with confidence fallback.
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

## MVP Flow

1. Admin logs in at `/admin` and receives a Bearer JWT.
2. Admin uploads a PDF or submits a file URL in `/admin`.
3. `upload-service` stores PDFs in GCS when credentials are configured.
4. `ingestion-service` extracts text, chunks it, and writes vectors to Qdrant.
5. User asks a question in `/chat`.
6. `rag-service` retrieves relevant chunks and returns an answer with citations.
7. Admin reviews answers in `Chat Logs`.

Admin upload, ingestion, and review APIs require a JWT with `ROLE_ADMIN`. Local defaults are `ADMIN_USERNAME=admin` and `ADMIN_PASSWORD=admin123`; change `JWT_SECRET_KEY` before any shared demo or deployment.

For easiest local testing without GCS, use the admin `file URL` field with a local text or PDF path that is visible inside the `ingestion-service` container, or call `POST /api/v1/ingest/` directly with an accessible `http`, `file`, `gs`, or container-local path.

## Import Hugging Face Legal Dataset

The ingestion service includes a small importer for `vohuutridung/vietnamese-legal-documents`. It imports a limited demo sample, filters common legal sectors, chunks the text, and upserts vectors into the Qdrant collection `legal_documents`.

Rebuild the ingestion image after dependency changes:

```bash
docker compose up -d --build ingestion-service
```

Import a small demo sample:

```bash
docker compose exec ingestion-service python scripts/import_hf_legal_documents.py \
  --limit 300 \
  --domains dan-su,dat-dai,lao-dong
```

Useful options:

```bash
--limit 200              # keep demo imports small; 200-1000 is enough for class demos
--domains ""             # disable domain filtering
--batch-size 64          # Qdrant upsert batch size
```

The importer stores these metadata fields in each Qdrant payload: `id`, `title`, `url`, `legal_type`, `legal_sectors`, `issuing_authority`, and `issuance_date`.

## Notes

- The services now use Vertex AI for embeddings and answer generation when credentials are available.
- If Vertex AI is unavailable, the backend falls back to deterministic local embeddings and a template answer so local development still works.
- Prompt files live in `rag-service/app/prompts/system_prompt.txt` and `rag-service/app/prompts/user_prompt.txt`.
- Chat history, ingestion jobs, and document registry are in memory for this first version.
- The bot is designed for legal lookup with citations, not personalized legal advice.
