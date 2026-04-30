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
