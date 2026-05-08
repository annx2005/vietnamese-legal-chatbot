output "upload_bucket_name" {
  description = "Tên bucket lưu trữ tài liệu"
  value       = module.upload_bucket.bucket_name
}

output "app_service_account_email" {
  description = "Email của App Service Account (dùng chạy ứng dụng)"
  value       = module.app_service_account.email
}

output "cicd_service_account_email" {
  description = "Email của CI/CD Service Account (dành cho GitHub Actions)"
  value       = module.cicd_service_account.email
}

output "wif_provider_name" {
  description = "Tên Workload Identity Provider để dùng trong GitHub Actions"
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "vpc_connector_id" {
  description = "ID của VPC Connector dùng cho Cloud Run để kết nối Redis"
  value       = google_vpc_access_connector.connector.id
}

output "redis_host" {
  description = "IP Host của Redis Memorystore"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Port của Redis Memorystore"
  value       = google_redis_instance.cache.port
}

output "db_connection_name" {
  description = "Connection Name của Cloud SQL (dùng cho Cloud SQL Auth Proxy)"
  value       = google_sql_database_instance.metadata_db.connection_name
}
