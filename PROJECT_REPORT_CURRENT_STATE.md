# Báo Cáo Hiện Trạng Project `legal-rag-chatbot`

Ngày tổng hợp: 2026-05-19

## 1. Mục đích và phạm vi

Tài liệu này mô tả trạng thái hiện tại của project `legal-rag-chatbot` dựa trên code đang có trong repository, không chỉ dựa trên ý tưởng kiến trúc hay README. Báo cáo tập trung vào:

- Thiết kế tổng thể
- Chức năng hiện có
- Luồng dữ liệu và luồng request
- Cách lưu trữ trạng thái
- Hạ tầng local và cloud
- Tích hợp AI hiện tại
- Điểm mạnh, hạn chế, rủi ro vận hành

Đây là báo cáo "as-built", tức là phản ánh hệ thống đang được triển khai trong code ở thời điểm hiện tại.

## 2. Tóm tắt điều hành

Project là một MVP chatbot pháp lý theo hướng RAG, gồm frontend React, gateway Kong, một số microservice backend, Qdrant làm vector store, Postgres cho auth metadata, và Google Cloud cho upload tài liệu, Vertex AI, cùng phần hạ tầng production.

Luồng sử dụng chính:

1. Admin nạp tài liệu bằng upload PDF hoặc nhập `file_url`.
2. `ingestion-service` đọc tài liệu, tách đoạn, tạo embedding và ghi vector vào Qdrant.
3. Người dùng hỏi ở màn `/chat`.
4. `rag-service` embed câu hỏi, tìm chunk liên quan trong Qdrant, rồi dùng Gemini trên Vertex AI để sinh câu trả lời có dẫn nguồn.

Project hiện đã chạy được flow lõi RAG, nhưng vẫn còn tính chất MVP rõ rệt:

- Nhiều trạng thái admin đang lưu trong RAM nên restart service sẽ mất khỏi UI.
- Auth mới ở mức skeleton, chưa bảo vệ thực tế các API.
- Upload đã publish Pub/Sub event nhưng ingestion chưa consume event đó.
- Settings UI mới là hiển thị tĩnh, chưa ghi ngược xuống backend.

## 3. Kiến trúc tổng thể

### 3.1 Thành phần chính

Các service được định nghĩa trong `docker-compose.yml`:

- `frontend`: ứng dụng React/Vite cho chat và admin
- `api-gateway`: Kong Gateway
- `auth-service`: Spring Boot auth service
- `upload-service`: Spring Boot upload PDF lên Google Cloud Storage
- `ingestion-service`: FastAPI ingestion pipeline
- `rag-service`: FastAPI RAG query service
- `postgres`: local PostgreSQL
- `qdrant`: vector database

Kiến trúc logic:

```text
Frontend
  -> Kong API Gateway
    -> auth-service
    -> upload-service
    -> ingestion-service
    -> rag-service

Ingestion / RAG
  -> Qdrant
  -> Vertex AI

Upload
  -> Google Cloud Storage
  -> Google Pub/Sub

Auth
  -> Postgres
```

### 3.2 Vai trò của từng lớp

- Frontend chịu trách nhiệm UI `/chat` và `/admin`.
- Kong làm reverse proxy thống nhất cho các API `/api/v1/*`.
- Upload service xử lý upload PDF và phát sự kiện.
- Ingestion service chuyển tài liệu thô thành chunks và embeddings.
- RAG service phục vụ truy vấn người dùng.
- Qdrant lưu vector và payload của chunks.
- Vertex AI cung cấp embedding model và generative model.
- Terraform định nghĩa hạ tầng cloud dùng cho môi trường gần production.

## 4. Cấu trúc chức năng hiện tại

### 4.1 Frontend

Frontend nằm trong `frontend/src/App.tsx` và `frontend/src/styles.css`.

Các màn hình chính:

- `/chat`
- `/admin`

#### `/chat`

Chức năng:

- Nhập câu hỏi pháp lý
- Gửi request tới `POST /api/v1/rag/query`
- Hiển thị:
  - câu trả lời
  - confidence
  - disclaimer
  - danh sách citations

Hành vi:

- Mặc định gửi `top_k = 5`
- Không gửi auth token
- Không có session chat nhiều lượt; mỗi request là độc lập

#### `/admin`

UI admin có 5 tab:

- `Dashboard`
- `Documents`
- `Jobs`
- `Chat Logs`
- `Settings`

##### Dashboard

Hiển thị số liệu tổng hợp từ:

- `GET /api/v1/ingest/admin/stats`
- `GET /api/v1/admin/stats`

Các metric:

- số tài liệu
- số chunk
- job lỗi
- job đang chạy
- tổng chat logs
- low confidence logs
- reviewed logs

##### Documents

Cho phép:

- upload PDF qua `POST /api/v1/upload/files`
- hoặc nhập `file_url` thủ công
- sau đó gọi `POST /api/v1/ingest/`
- xem danh sách tài liệu
- disable tài liệu khỏi kết quả RAG

Lưu ý:

- `disable` chỉ cập nhật registry trong RAM của ingestion-service
- payload trong Qdrant không được cập nhật ngược hàng loạt khi disable

##### Jobs

Cho phép:

- xem danh sách job ingest
- retry một job qua `POST /api/v1/ingest/jobs/{task_id}/retry`

##### Chat Logs

Cho phép:

- xem câu hỏi và câu trả lời đã hỏi
- gắn nhãn review:
  - `correct`
  - `missing_source`
  - `unsafe`
  - `needs_review`

##### Settings

Hiện tại chỉ là form tĩnh hiển thị:

- top K
- confidence threshold
- embedding model
- LLM model
- disclaimer

Form này chưa nối backend và chưa lưu cấu hình.

### 4.2 API Gateway

Gateway dùng Kong với cấu hình declarative trong `kong-gateway/kong.yml`.

Routing hiện có:

- `/api/v1/auth` -> `auth-service:8080`
- `/api/v1/upload` -> `upload-service:8080`
- `/api/v1/rag` -> `rag-service:8000`
- `/api/v1/ingest` -> `ingestion-service:8000`
- `/api/v1/admin` -> `rag-service:8000`

Plugin hiện bật:

- `cors` với `origins: *`

Kong đóng vai trò entrypoint hợp nhất. Auth hiện được enforce ở từng service bằng Bearer JWT, chưa dùng auth gateway policy nâng cao.

### 4.3 Auth Service

`auth-service` là một Spring Boot service.

Endpoint chính:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/login/register`

Hành vi hiện tại:

- `login` trả JWT HS256 gồm `sub`, `role`, `iat`, `exp`
- `register` lưu user vào Postgres
- password được hash bằng BCrypt
- admin mặc định được seed từ `ADMIN_USERNAME` và `ADMIN_PASSWORD`
- các endpoint admin/upload/ingest yêu cầu Bearer JWT có `role=ROLE_ADMIN`

Security config của `auth-service` vẫn mở cho login/register, còn authorization thực tế nằm ở các service tiêu thụ JWT.

Auth service hiện đủ cho local/demo admin gate, nhưng chưa phải module bảo mật production-ready vì chưa có refresh token, revoke token, key rotation hoặc OAuth/OIDC.

### 4.4 Upload Service

`upload-service` là Spring Boot service để upload PDF.

Endpoint chính:

- `POST /api/v1/upload/files`

Luồng xử lý:

1. Validate file không rỗng
2. Chỉ chấp nhận `.pdf`
3. Sinh `documentId`
4. Upload file lên GCS bucket
5. Tạo `gs://bucket/object`
6. Publish `DocumentUploadedEvent` lên Pub/Sub
7. Trả về metadata upload cho frontend

Điểm đáng chú ý:

- Service cần Google Cloud credentials hợp lệ
- File được lưu trên GCS thật chứ không phải local disk
- Event Pub/Sub đã được publish, nhưng downstream consumer chưa được nối trong code hiện tại

### 4.5 Ingestion Service

`ingestion-service` là FastAPI service phụ trách pipeline xử lý tài liệu.

Endpoint hiện có:

- `POST /api/v1/ingest/`
- `GET /api/v1/ingest/jobs`
- `POST /api/v1/ingest/jobs/{task_id}/retry`
- `GET /api/v1/ingest/documents`
- `POST /api/v1/ingest/documents/{document_id}/disable`
- `GET /api/v1/ingest/admin/stats`
- `GET /api/v1/ingest/health`

#### Luồng ingest hiện tại

1. Nhận `file_url`, `document_id`, `document_type`, `metadata`
2. Tạo `DocumentRecord` và `IngestionJob` trong RAM
3. Đọc file từ một trong các nguồn:
   - `http`
   - `https`
   - `gs`
   - `file://`
   - local path trong container
4. Nếu là PDF thì extract text bằng `pdfplumber`
5. Chuẩn hóa khoảng trắng
6. Chunk văn bản theo paragraph với:
   - `CHUNK_SIZE = 1200`
   - `CHUNK_OVERLAP = 160`
7. Tạo embedding theo batch bằng Vertex AI
8. Nếu Vertex lỗi thì fallback sang local deterministic embedding
9. Upsert các point vào Qdrant

#### Payload lưu trong Qdrant

Mỗi chunk lưu:

- `document_id`
- `title`
- `source_url`
- `domain`
- `article`
- `chunk_index`
- `effective_status`
- `content`
- `enabled`

#### Cách tạo point id

Point id được tạo ổn định theo:

```text
uuid5(document_id:chunk_index)
```

Điều này cho phép ingest lại cùng `document_id` sẽ overwrite point cũ thay vì nhân bản vô hạn.

#### Registry trạng thái

Hai biến global hiện giữ trạng thái:

- `DOCUMENTS`
- `JOBS`

Chúng là in-memory dict. Vì vậy:

- restart `ingestion-service` sẽ mất danh sách documents/jobs trên UI
- nhưng dữ liệu vector trong Qdrant vẫn còn nếu volume không bị xóa

### 4.6 RAG Service

`rag-service` là FastAPI service trả lời câu hỏi.

Endpoint hiện có:

- `POST /api/v1/rag/query`
- `GET /api/v1/rag/admin/chat-logs`
- `POST /api/v1/rag/admin/chat-logs/{log_id}/review`
- `GET /api/v1/rag/admin/stats`
- `GET /api/v1/rag/health`

Và một nhánh admin riêng cũng expose:

- `GET /api/v1/admin/chat-logs`
- `POST /api/v1/admin/chat-logs/{log_id}/review`
- `GET /api/v1/admin/stats`

#### Luồng query

1. Nhận `query`, `top_k`, `filters`
2. Tạo embedding cho query bằng Vertex AI
3. Nếu Vertex lỗi thì fallback local embedding
4. Search Qdrant collection `legal_documents`
5. Biến kết quả thành `SourceDocument` và `Citation`
6. Lấy confidence là score cao nhất của hits
7. Nếu confidence dưới ngưỡng `0.18` hoặc không có citation:
   - trả câu trả lời low-confidence
   - không cố khẳng định
8. Nếu confidence đạt ngưỡng:
   - render prompt
   - gọi Gemini trên Vertex AI để sinh câu trả lời
9. Nếu Gemini lỗi:
   - fallback sang câu trả lời template dựng từ citation
10. Lưu chat log vào RAM

#### Prompt hiện tại

Prompt được tách thành file riêng:

- `rag-service/app/prompts/system_prompt.txt`
- `rag-service/app/prompts/user_prompt.txt`

Ưu điểm:

- dễ chỉnh prompt mà không phải sửa logic Python
- prompt rendering có ngữ cảnh citations top 5

#### Chat logs

Chat logs được giữ trong biến global `CHAT_LOGS`.

Tác động:

- restart service sẽ mất lịch sử hỏi đáp trên UI
- không có persistence sang Postgres hay Redis

## 5. Tích hợp AI hiện tại

### 5.1 Embedding

Project hiện dùng Vertex AI thật cho embedding khi credentials hợp lệ.

Model mặc định:

- `text-embedding-005`

Áp dụng tại:

- ingestion chunks
- rag query embedding
- Hugging Face importer

Fallback:

- deterministic local embedding hash-based

Fallback này giúp môi trường local vẫn chạy được nếu Vertex lỗi, nhưng chất lượng retrieval thấp hơn đáng kể.

### 5.2 Answer generation

Project hiện dùng Vertex AI Gemini để generate câu trả lời.

Model mặc định:

- `gemini-2.5-flash`

Các config chính:

- `LLM_TEMPERATURE = 0.2`
- `LLM_MAX_OUTPUT_TOKENS = 1024`

Nếu model trả response rỗng hoặc lỗi:

- service fallback sang answer template dựng từ citation

### 5.3 Điều kiện để gọi Vertex AI

Để gọi được Vertex AI, runtime cần:

- `PROJECT_ID` hoặc `GCP_PROJECT_ID`
- `GCP_REGION` đang được map sang `GCP_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS`
- quyền `roles/aiplatform.user`

Nếu local chỉ chạy Docker mà không có credentials hợp lệ, app có thể vẫn chạy nhưng chất lượng AI sẽ giảm vì fallback.

## 6. Dữ liệu và lưu trữ

### 6.1 Qdrant

Qdrant là thành phần lưu tri thức RAG thực tế.

Local compose mount volume:

- `qdrant_data:/qdrant/storage`

Điều này có nghĩa:

- `docker compose stop/start` giữ dữ liệu
- `docker compose down/up` vẫn giữ dữ liệu nếu không xóa volume
- `docker compose down -v` sẽ xóa dữ liệu Qdrant

Collection mặc định:

- `legal_documents`

### 6.2 Postgres

Postgres local có volume:

- `postgres_data:/var/lib/postgresql/data`

Hiện tại Postgres chủ yếu được `auth-service` dùng để lưu user.

Project chưa lưu vào Postgres các thực thể sau:

- document registry
- ingestion jobs
- chat logs
- review audit

### 6.3 Google Cloud Storage

GCS được dùng cho:

- lưu file PDF upload từ `upload-service`

Khi dùng admin upload PDF, file sẽ được đẩy lên bucket cloud thay vì lưu local.

### 6.4 Pub/Sub

Pub/Sub được dùng bởi `upload-service` để publish event `DocumentUploadedEvent`.

Tuy nhiên hiện chưa có ingestion worker subscribe thật từ subscription để tự động ingest từ event đó. Vì vậy hệ thống hiện chưa hoàn chỉnh theo mô hình event-driven.

## 7. Luồng nghiệp vụ chi tiết

### 7.1 Luồng chat

```text
User nhập câu hỏi ở /chat
-> frontend gọi POST /api/v1/rag/query
-> Kong forward sang rag-service
-> rag-service embed query
-> rag-service search Qdrant
-> rag-service render prompt từ citations
-> rag-service gọi Gemini
-> rag-service trả answer + citations + confidence + disclaimer
-> frontend render kết quả
```

### 7.2 Luồng upload PDF từ admin

```text
Admin chọn file PDF ở /admin
-> frontend gọi POST /api/v1/upload/files
-> upload-service upload file lên GCS
-> upload-service publish Pub/Sub event
-> frontend nhận gs:// URL
-> frontend gọi POST /api/v1/ingest/
-> ingestion-service đọc file từ GCS
-> extract text -> chunk -> embed -> upsert Qdrant
```

Điểm quan trọng: chính frontend đang chủ động gọi ingest sau upload; ingestion chưa tự subscribe từ Pub/Sub.

### 7.3 Luồng ingest từ file URL

```text
Admin nhập file URL
-> frontend gọi POST /api/v1/ingest/
-> ingestion-service tự đọc URL
-> extract/chunk/embed
-> upsert Qdrant
```

Nguồn có thể là:

- `http(s)://...`
- `gs://...`
- `file://...`
- local path trong container

### 7.4 Luồng import Hugging Face dataset

Script:

- `ingestion-service/scripts/import_hf_legal_documents.py`

Dataset:

- `vohuutridung/vietnamese-legal-documents`

Flow:

1. Load split `metadata`
2. Lọc document theo domain
3. Load split `content`
4. Chunk text
5. Tạo embedding bằng Vertex AI
6. Upsert vào Qdrant

Tuỳ chọn:

- `--limit`
- `--domains`
- `--batch-size`
- `--embedding-batch-size`
- `--allow-local-embedding-fallback`

Importer hiện đã được đồng bộ để ưu tiên Vertex embedding, tránh mismatch vector space với query embedding.

## 8. Cấu hình runtime

### 8.1 Cấu hình Docker Compose

`docker-compose.yml` hiện chịu trách nhiệm:

- build local images
- mount Google ADC file vào container
- khai báo networking nội bộ
- expose ports cho local dev

Các env quan trọng:

- `PROJECT_ID`
- `GCP_REGION`
- `UPLOAD_BUCKET_NAME`
- `COLLECTION_NAME`
- `EMBEDDING_MODEL_NAME`
- `LLM_MODEL_NAME`

`rag-service` và `ingestion-service` đang map:

- `GCP_LOCATION=${GCP_REGION:-asia-southeast1}`

### 8.2 Region

Runtime hiện đã được đồng bộ về:

- `asia-southeast1`

Việc đồng bộ region là quan trọng vì model availability, latency và billing trong Vertex AI phụ thuộc location.

### 8.3 Model mặc định

Mặc định hiện tại:

- Embedding: `text-embedding-005`
- LLM: `gemini-2.5-flash`

## 9. Hạ tầng cloud qua Terraform

Terraform trong thư mục `terraform/` tạo một bộ hạ tầng GCP tương đối đầy đủ.

### 9.1 Tài nguyên chính

- GCS bucket cho uploads
- App Service Account
- CI/CD Service Account
- IAM bindings cho Storage, Vertex AI, Cloud SQL, Secret Manager
- Artifact Registry repository
- Pub/Sub topic và subscription
- Cloud SQL PostgreSQL instance
- Secret Manager secrets
- Workload Identity Federation cho GitHub Actions

### 9.2 Ý nghĩa hạ tầng

Terraform phản ánh định hướng production:

- upload tài liệu qua GCS
- event qua Pub/Sub
- deploy service lên Cloud Run
- dùng Vertex AI thật
- có Postgres managed

Tuy nhiên code ứng dụng hiện chưa tận dụng hết toàn bộ hạ tầng đã provision.

Ví dụ:

- Memorystore được tạo nhưng app chưa dùng sâu
- Pub/Sub subscription có tạo nhưng ingestion không consume
- Cloud SQL được tạo nhưng ngoài auth ra chưa lưu metadata vận hành chính

### 9.3 Tác động chi phí

Một số tài nguyên cloud có thể phát sinh usage dù app local không dùng trực tiếp, đặc biệt:

- Cloud SQL
- Cloud Run nếu đã deploy
- Networking liên quan

Nếu account còn credit/free savings thì subtotal có thể vẫn bằng 0, nhưng usage là usage thật.

## 10. CI/CD và deploy

GitHub Actions workflow:

- `.github/workflows/deploy-cloud-run.yml`

Flow:

1. Trigger khi push `main` có thay đổi ở `auth-service`, `upload-service`, `ingestion-service`, `rag-service`
2. Authenticate GCP qua Workload Identity Federation
3. Docker auth vào Artifact Registry
4. Build image từng service
5. Push image
6. Deploy lên Cloud Run

Deploy hiện áp dụng cho:

- `upload-service`
- `auth-service`
- `ingestion-service`
- `rag-service`

Cloud Run flags đang dùng:

- `--allow-unauthenticated`
- `--service-account=<APP_SERVICE_ACCOUNT>`

Điểm cần lưu ý:

- Workflow chưa thể hiện đầy đủ toàn bộ runtime env secrets cho từng service
- Một số cấu hình production có thể đang phụ thuộc cấu hình tay trên GCP ngoài repo

## 11. Bảo mật và quyền truy cập

### 11.1 Hiện trạng

Bảo mật hiện tại ở mức MVP:

- frontend có admin login flow
- auth-service trả JWT HS256
- password được hash bằng BCrypt
- admin/upload/ingest routes kiểm tra Bearer JWT có `ROLE_ADMIN`
- Kong chưa áp policy auth
- CORS mở rộng

### 11.2 Rủi ro

- không phù hợp production internet-facing
- admin actions có thể bị gọi trực tiếp nếu route public
- dữ liệu user auth chưa được bảo vệ đúng chuẩn

### 11.3 Phần an toàn tương đối

- dùng service account cho GCP
- có IAM role rõ ràng trong Terraform
- có Secret Manager cho cloud secret

Nhưng phần application-layer security vẫn cần làm thêm rất nhiều.

## 12. Quan sát về độ bền dữ liệu

Đây là điểm rất dễ gây hiểu nhầm khi vận hành local.

### 12.1 Cái gì còn sau restart

Nếu không xóa volume Docker:

- Qdrant vectors còn
- Postgres auth data còn

### 12.2 Cái gì mất sau restart service

Do đang để trong RAM:

- danh sách documents trên admin
- ingestion jobs
- chat logs
- review status

Kết quả là:

- dữ liệu tri thức để trả lời có thể vẫn còn trong Qdrant
- nhưng UI admin trông như “mất dữ liệu”

Đây là hạn chế lớn của bản MVP.

## 13. Chất lượng trả lời và hành vi fallback

### 13.1 Khi đủ ngữ cảnh

Hệ thống:

- retrieve chunks từ Qdrant
- xây prompt có context
- gọi Gemini
- trả lời kèm citation

### 13.2 Khi confidence thấp

Nếu top score dưới ngưỡng:

- hệ thống trả câu "chưa đủ căn cứ"
- không cố tạo đáp án chắc chắn

Đây là một lựa chọn an toàn hợp lý cho chatbot pháp lý.

### 13.3 Khi AI cloud lỗi

Nếu Vertex AI lỗi:

- embedding có thể fallback local
- generate có thể fallback answer template

Điều này giúp hệ thống không chết hẳn, nhưng cần hiểu rằng lúc đó chất lượng không tương đương chạy Vertex thật.

## 14. Hạn chế kỹ thuật hiện tại

### 14.1 Hạn chế về persistence

- admin state không bền
- chat logs không bền
- document registry không bền
- không có audit persistence

### 14.2 Hạn chế về auth

- JWT đang dùng shared secret HS256 đơn giản
- chưa có refresh token
- chưa có token revocation/logout phía server
- chưa có key rotation hoặc OAuth/OIDC production-grade

### 14.3 Hạn chế về event-driven design

- upload có publish Pub/Sub
- nhưng ingestion chưa có consumer
- chưa có background worker thực sự

### 14.4 Hạn chế về search/retrieval

- metadata filter còn đơn giản
- chưa có reranker
- confidence chỉ là top score
- chưa có multi-query retrieval

### 14.5 Hạn chế về data lifecycle

- disable document mới phản ánh ở registry RAM
- chưa có cơ chế xóa/disable đồng bộ tất cả payload trong Qdrant
- chưa có versioning document

### 14.6 Hạn chế về vận hành cloud

- infra cloud provision khá nhiều nhưng app chưa dùng hết
- có nguy cơ tốn chi phí nền nếu không dọn tài nguyên
- workflow deploy chưa thể hiện đầy đủ cấu hình runtime

## 15. Điểm mạnh của thiết kế hiện tại

- Chia tách service tương đối rõ chức năng
- RAG flow lõi đã hoạt động được
- Prompt được tách file riêng
- Vertex AI đã được nối thật cho cả embed và generate
- Có importer từ Hugging Face để seed corpus nhanh
- Docker Compose cho local dev tương đối tiện
- Terraform và GitHub Actions đã đặt nền cho production

## 16. Gợi ý ưu tiên phát triển tiếp

### 16.1 Ưu tiên rất cao

1. Lưu `documents`, `jobs`, `chat_logs`, `reviews` vào Postgres
2. Làm auth thật:
   - password hashing
   - JWT thật
   - phân quyền admin/user
3. Bảo vệ admin routes và gateway

### 16.2 Ưu tiên cao

1. Implement Pub/Sub consumer cho ingestion tự động
2. Đồng bộ thao tác disable/xóa document với Qdrant payload
3. Thêm migration/schema rõ ràng cho metadata

### 16.3 Ưu tiên trung bình

1. Nối Settings UI với backend/config store
2. Thêm observability:
   - structured logs
   - request tracing
   - token usage logging
3. Thêm evaluation set cho RAG

### 16.4 Ưu tiên tối ưu chi phí

1. Rà soát tài nguyên GCP luôn-on
2. Tắt Memorystore/VPC connector/Cloud SQL khi chưa cần
3. Chỉ giữ Cloud Run và Vertex AI cho môi trường thật sự cần demo online

## 17. Kết luận

`legal-rag-chatbot` hiện là một MVP có nền tảng khá rõ: UI chat/admin, ingestion pipeline, Qdrant retrieval, và sinh câu trả lời bằng Gemini. Hệ thống đã vượt qua mức demo tĩnh vì có flow upload, indexing, retrieval và generation chạy thật với Vertex AI.

Tuy nhiên, trạng thái hiện tại vẫn mang tính "prototype vận hành được" hơn là production-ready. Phần lõi RAG đã có, nhưng persistence, auth, event-driven orchestration và hardening vận hành vẫn còn thiếu. Điều này không phải vấn đề nếu mục tiêu hiện tại là demo, PoC hoặc phát triển nội bộ; nhưng nếu muốn đưa ra môi trường thực tế, cần ưu tiên nâng cấp persistence, bảo mật và đồng bộ state trước.

## 18. Phụ lục: các file chính cần biết

### Runtime local

- `docker-compose.yml`
- `README.md`
- `.env.example`

### Frontend

- `frontend/src/App.tsx`
- `frontend/src/styles.css`

### Gateway

- `kong-gateway/kong.yml`

### RAG

- `rag-service/app/main.py`
- `rag-service/app/api/main.py`
- `rag-service/app/api/routes/rag.py`
- `rag-service/app/api/routes/admin.py`
- `rag-service/app/services/rag_service.py`
- `rag-service/app/services/vertex_ai_service.py`
- `rag-service/app/services/prompt_service.py`
- `rag-service/app/prompts/system_prompt.txt`
- `rag-service/app/prompts/user_prompt.txt`

### Ingestion

- `ingestion-service/app/main.py`
- `ingestion-service/app/api/main.py`
- `ingestion-service/app/api/routes/ingest.py`
- `ingestion-service/app/services/ingestion_service.py`
- `ingestion-service/app/services/vertex_ai_service.py`
- `ingestion-service/scripts/import_hf_legal_documents.py`

### Upload/Auth

- `upload-service/src/main/java/com/example/upload_service/service/UploadService.java`
- `upload-service/src/main/java/com/example/upload_service/controller/UploadController.java`
- `auth-service/src/main/java/com/example/auth_service/service/AuthService.java`
- `auth-service/src/main/java/com/example/auth_service/controller/AuthController.java`
- `auth-service/src/main/java/com/example/auth_service/config/SecurityConfig.java`

### Infra và deploy

- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/outputs.tf`
- `.github/workflows/deploy-cloud-run.yml`
