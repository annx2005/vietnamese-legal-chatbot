# 🚀 Phân Tích Deploy Lên Cloud Run

## Tổng Quan Kiến Trúc

Project hiện tại gồm 6 services:

| Service | Ngôn ngữ | Trạng thái trong CI/CD |
|---|---|---|
| `auth-service` | Java/Spring Boot | ✅ Đã có trong workflow |
| `upload-service` | Java/Spring Boot | ✅ Đã có trong workflow |
| `rag-service` | Python/FastAPI | ✅ Đã có trong workflow |
| `ingestion-service` | Python | ✅ Đã có trong workflow |
| `frontend` | Vite/React | ❌ **Chưa có** |
| `api-gateway` (Kong) | Kong | ❌ **Chưa có / Cần xử lý khác** |

Infrastructure đang dùng:
- **Cloud SQL** (PostgreSQL) → ✅ Đã có Terraform
- **Qdrant** (Vector DB) → ❌ **Chưa có giải pháp cloud**
- **GCS Bucket** → ✅ Đã có Terraform
- **Pub/Sub** → ✅ Đã có Terraform
- **Artifact Registry** → ✅ Đã có Terraform
- **Secret Manager** → ✅ Đã có Terraform (DB password)

---

## ❌ Vấn Đề 1: Qdrant Chưa Có Giải Pháp Cloud

**Đây là vấn đề lớn nhất.** Hiện tại Qdrant chạy local qua Docker Compose.  
Trên Cloud Run, không có container Qdrant nào.

### Giải pháp (chọn 1):

**Option A – Qdrant Cloud (Khuyến nghị, dễ nhất):**
1. Đăng ký tại [cloud.qdrant.io](https://cloud.qdrant.io) (free tier: 1GB)
2. Lấy `QDRANT_URL` và `QDRANT_API_KEY`
3. Lưu vào Secret Manager
4. Truyền vào `rag-service` và `ingestion-service` qua `--set-secrets`

**Option B – Deploy Qdrant lên Cloud Run:**
- Dùng image `qdrant/qdrant` deploy lên Cloud Run
- Mount volume qua Cloud Storage FUSE (phức tạp, latency cao)
- ⚠️ Không phù hợp cho production vì Cloud Run stateless

**Option C – GKE / Compute Engine:**
- Tốn chi phí hơn, phù hợp nếu scale lớn

---

## ❌ Vấn Đề 2: Kong API Gateway Không Phù Hợp Cloud Run

Kong trong Docker Compose dùng config file tĩnh (`kong.yml`) với hostname nội bộ (`http://auth-service:8080`).  
Trên Cloud Run, mỗi service có URL riêng dạng `https://<service>-<hash>-<region>.run.app`.

### Giải pháp (chọn 1):

**Option A – Thay Kong bằng Cloud Run Ingress / Load Balancer (Khuyến nghị):**
- Dùng **Google Cloud Load Balancer** + **URL Maps** để route traffic
- Frontend gọi trực tiếp từng Cloud Run service URL
- Cần cập nhật frontend config

**Option B – Deploy Kong lên Cloud Run với config động:**
- Thay hostname trong `kong.yml` bằng Cloud Run URLs thật
- Dùng environment variable để inject URLs vào kong config lúc startup
- Cần viết entrypoint script cho Kong container

**Option C – Đơn giản nhất: Bỏ Kong, Frontend gọi trực tiếp:**
- Frontend store các Cloud Run service URLs trong env vars
- Mất centralized auth/routing nhưng đơn giản hơn nhiều

---

## ❌ Vấn Đề 3: Frontend Dockerfile Chưa Production-Ready

```dockerfile
# Hiện tại (DEV mode – KHÔNG phù hợp cho production/Cloud Run)
FROM node:22-alpine
CMD ["npm", "run", "dev"]  # ← Vite dev server, không dùng cho prod
```

Cần đổi sang multi-stage build với Nginx:

```dockerfile
# Stage 1: Build
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: Serve với Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

**Lưu ý:** Cloud Run mặc định dùng port **8080**, không phải 5173.

---

## ❌ Vấn Đề 4: Secrets Còn Thiếu Trong Workflow

Workflow hiện tại chỉ pass `DB_PASSWORD`. Còn thiếu:

| Secret | Dùng cho | Cần thêm vào Secret Manager? |
|---|---|---|
| `JWT_SECRET_KEY` | auth, upload, rag, ingestion | ✅ Có |
| `QDRANT_API_KEY` | rag, ingestion | ✅ Có (placeholder đã tạo) |
| `QDRANT_URL` | rag, ingestion | ✅ Có (placeholder đã tạo) |
| `ADMIN_USERNAME` | auth-service | ✅ Có |
| `ADMIN_PASSWORD` | auth-service | ✅ Có |

---

## ❌ Vấn Đề 5: `ingestion-service` Thiếu Cấu Hình Pub/Sub

Trong workflow, `ingestion-service` có `env_vars: ""` và `secrets: ""`.  
Service này cần:
- `PUBSUB_SUBSCRIPTION_NAME`
- `GCS_BUCKET_NAME`
- `QDRANT_URL`, `QDRANT_API_KEY`

---

## ❌ Vấn Đề 6: `upload-service` Thiếu Env Vars

Trong workflow, `upload-service` có `env_vars: ""`.  
Service này cần:
- `PROJECT_ID`
- `UPLOAD_BUCKET_NAME`
- `PUBSUB_TOPIC_NAME`
- `JWT_SECRET_KEY` (dạng secret)

---

## ✅ Checklist Triển Khai Đầy Đủ

### Bước 1: Chuẩn Bị Qdrant Cloud
- [ ] Tạo cluster tại cloud.qdrant.io
- [ ] Lưu `QDRANT_URL` vào Secret Manager: `gcloud secrets versions add qdrant-url-prod --data-file=-`
- [ ] Lưu `QDRANT_API_KEY` vào Secret Manager

### Bước 2: Lưu Các Secrets Còn Thiếu
```bash
# JWT Secret
echo -n "your-super-secret-jwt-key" | gcloud secrets create jwt-secret-key-prod --data-file=-

# Admin credentials
echo -n "admin" | gcloud secrets create admin-username-prod --data-file=-
echo -n "your-admin-password" | gcloud secrets create admin-password-prod --data-file=-
```

### Bước 3: Cập Nhật Frontend Dockerfile
- [ ] Tạo `frontend/nginx.conf` với cấu hình SPA routing
- [ ] Sửa `frontend/Dockerfile` sang multi-stage build
- [ ] Xác định frontend sẽ gọi API qua URL nào (Kong URL hoặc trực tiếp)

### Bước 4: Quyết Định Chiến Lược API Gateway
- [ ] Nếu giữ Kong: Viết script generate `kong.yml` từ Cloud Run URLs
- [ ] Nếu bỏ Kong: Frontend cần biết URL của từng service

### Bước 5: Cập Nhật Workflow `.github/workflows/deploy-cloud-run.yml`
- [ ] Thêm `frontend` vào matrix
- [ ] Thêm env_vars và secrets cho `upload-service`
- [ ] Thêm env_vars và secrets cho `ingestion-service`
- [ ] Thêm `JWT_SECRET_KEY` secret cho tất cả services
- [ ] Thêm `QDRANT_URL` và `QDRANT_API_KEY` cho rag và ingestion

### Bước 6: Thêm `frontend` vào CI/CD paths trigger
```yaml
paths:
  - "frontend/**"   # ← Thêm cái này
```

### Bước 7: Đảm Bảo Các GitHub Secrets Đã Set
Tại `Settings > Secrets and variables > Actions` không cần vì dùng WIF (đã có).

---

## 📋 Updated Workflow Matrix (Đề Xuất)

```yaml
matrix:
  include:
    - service: auth-service
      cloudsql: "legal-chatbot-496302:asia-southeast1:legal-rag-db-prod"
      env_vars: "DATABASE_URL=jdbc:postgresql:///metadata_db?socketFactory=...,...,ADMIN_USERNAME=admin"
      secrets: "DB_PASSWORD=legal-rag-db-password-prod:latest,JWT_SECRET_KEY=jwt-secret-key-prod:latest,ADMIN_PASSWORD=admin-password-prod:latest"

    - service: upload-service
      cloudsql: ""
      env_vars: "PROJECT_ID=legal-chatbot-496302,UPLOAD_BUCKET_NAME=legal-rag-uploads-prod,PUBSUB_TOPIC_NAME=legal-document-uploaded-prod"
      secrets: "JWT_SECRET_KEY=jwt-secret-key-prod:latest"

    - service: ingestion-service
      cloudsql: ""
      env_vars: "GCP_PROJECT_ID=legal-chatbot-496302,GCP_LOCATION=asia-southeast1,GCS_BUCKET_NAME=legal-rag-uploads-prod,EMBEDDING_MODEL_NAME=text-embedding-005"
      secrets: "QDRANT_URL=qdrant-url-prod:latest,QDRANT_API_KEY=qdrant-api-key-prod:latest"

    - service: rag-service
      cloudsql: "legal-chatbot-496302:asia-southeast1:legal-rag-db-prod"
      env_vars: "DATABASE_URL=postgresql+psycopg2://legal_app_user:DB_PASSWORD_PLACEHOLDER@/metadata_db?host=/cloudsql/...,GCP_PROJECT_ID=legal-chatbot-496302,GCP_LOCATION=asia-southeast1,EMBEDDING_MODEL_NAME=text-embedding-005,LLM_MODEL_NAME=gemini-2.5-flash"
      secrets: "DB_PASSWORD=legal-rag-db-password-prod:latest,JWT_SECRET_KEY=jwt-secret-key-prod:latest,QDRANT_URL=qdrant-url-prod:latest,QDRANT_API_KEY=qdrant-api-key-prod:latest"

    - service: frontend
      cloudsql: ""
      env_vars: "..."   # URL của các services
      secrets: ""
```

---

## 🔑 Tóm Tắt Ưu Tiên

| Mức độ | Vấn đề |
|---|---|
| 🔴 Blocking | Qdrant chưa có trên cloud → services không start được |
| 🔴 Blocking | Frontend Dockerfile dùng dev server → không chạy được |
| 🟠 High | Secrets thiếu (JWT, Qdrant) → services crash |
| 🟠 High | `upload-service` và `ingestion-service` thiếu env vars |
| 🟡 Medium | API Gateway strategy chưa rõ cho cloud |
| 🟢 Low | Thêm `frontend` vào CI/CD paths trigger |
