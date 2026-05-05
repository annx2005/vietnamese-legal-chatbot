# 1. Tạo GCS Bucket để lưu trữ tài liệu PDF
module "upload_bucket" {
  source      = "./modules/gcs_bucket"
  bucket_name = var.bucket_name
  location    = var.region
}

# 2. Tạo Service Account cho các ứng dụng (Upload, Ingestion, RAG)
module "app_service_account" {
  source       = "./modules/service_account"
  account_id   = "legal-rag-app-${var.environment}"
  display_name = "Legal RAG App Service Account (${var.environment})"
}

# 3. Gán quyền Storage Object Admin cho Service Account trên bucket
module "app_storage_binding" {
  source                = "./modules/iam_binding"
  bucket_name           = module.upload_bucket.bucket_name
  role                  = "roles/storage.objectAdmin"
  service_account_email = module.app_service_account.email
}

# 4. Gán quyền truy cập Vertex AI cho Service Account (để gọi mô hình AI)
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${module.app_service_account.email}"
}

# =========================================================================
# 5. KÍCH HOẠT CÁC API DỊCH VỤ GCP
# =========================================================================
resource "google_project_service" "services" {
  for_each = toset([
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "iamcredentials.googleapis.com" # Yêu cầu cho Workload Identity
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# =========================================================================
# 6. ARTIFACT REGISTRY (LƯU TRỮ DOCKER IMAGE)
# =========================================================================
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "legal-rag-repo-${var.environment}"
  description   = "Docker repository for Legal RAG Microservices"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

# =========================================================================
# 7. PUB/SUB (EVENT DRIVEN UPLOAD -> INGESTION)
# =========================================================================
resource "google_pubsub_topic" "document_uploaded" {
  name       = "legal-document-uploaded-${var.environment}"
  project    = var.project_id
  depends_on = [google_project_service.services]
}

resource "google_pubsub_subscription" "document_ingestion_sub" {
  name                 = "legal-document-ingestion-sub-${var.environment}"
  topic                = google_pubsub_topic.document_uploaded.name
  project              = var.project_id
  ack_deadline_seconds = 60
}

resource "google_pubsub_topic_iam_member" "sa_publisher" {
  topic   = google_pubsub_topic.document_uploaded.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${module.app_service_account.email}"
}

resource "google_pubsub_subscription_iam_member" "sa_subscriber" {
  subscription = google_pubsub_subscription.document_ingestion_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${module.app_service_account.email}"
}

# =========================================================================
# 8. CLOUD SQL (POSTGRESQL CHO METADATA)
# =========================================================================
resource "google_sql_database_instance" "metadata_db" {
  name             = "legal-rag-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro" # Cấu hình thấp nhất để tiết kiệm chi phí
    ip_configuration {
      ipv4_enabled = true # Cho phép Public IP để dev local có thể kết nối dễ dàng
    }
  }
  depends_on = [google_project_service.services]
  deletion_protection = false # Đặt false để có thể xóa nhanh khi test
}

resource "google_sql_database" "database" {
  name     = "metadata_db"
  instance = google_sql_database_instance.metadata_db.name
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "google_sql_user" "users" {
  name     = "legal_app_user"
  instance = google_sql_database_instance.metadata_db.name
  password = random_password.db_password.result
}

# =========================================================================
# 9. REDIS MEMORYSTORE (LƯU CHAT HISTORY)
# =========================================================================
resource "google_redis_instance" "cache" {
  name           = "legal-rag-cache-${var.environment}"
  tier           = "BASIC" # Cấu hình Basic không có HA, tiết kiệm tiền
  memory_size_gb = 1
  region         = var.region
  depends_on     = [google_project_service.services]
}

# =========================================================================
# 10. SECRET MANAGER (LƯU TRỮ KEYS & PASSWORD)
# =========================================================================
# Tự động lưu Password Database vào Secret Manager
resource "google_secret_manager_secret" "db_password_secret" {
  secret_id = "legal-rag-db-password-${var.environment}"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password_secret.id
  secret_data = random_password.db_password.result
}

# Placeholder Secret cho Qdrant API Key
resource "google_secret_manager_secret" "qdrant_api_key" {
  secret_id = "qdrant-api-key-${var.environment}"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

# Gán quyền đọc Secrets cho Service Account của App
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${module.app_service_account.email}"
}

# =========================================================================
# 11. WORKLOAD IDENTITY FEDERATION (GCP -> GITHUB ACTIONS)
# =========================================================================
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool-${var.environment}"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions deployments"
  depends_on                = [google_project_service.services]
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "attribute.repository == '${var.github_repo}'"
  
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Cấp quyền cho Repo GitHub mượn vai (Assume Role) của Service Account
# (Do policy module/resource, ta cần lấy id của service account theo format chuẩn)
data "google_service_account" "app_sa_data" {
  account_id = module.app_service_account.email
}

resource "google_service_account_iam_member" "github_actions_sa_binding" {
  service_account_id = data.google_service_account.app_sa_data.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_repo}"
}

# Cấp thêm các quyền cần thiết để CI/CD có thể triển khai Cloud Run và đẩy ảnh Docker
resource "google_project_iam_member" "cloud_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${module.app_service_account.email}"
}

resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${module.app_service_account.email}"
}

resource "google_project_iam_member" "service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${module.app_service_account.email}"
}
