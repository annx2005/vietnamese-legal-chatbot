output "upload_bucket_name" {
  description = "Tên bucket lưu trữ tài liệu"
  value       = module.upload_bucket.bucket_name
}

output "service_account_email" {
  description = "Email của Service Account dùng cho ứng dụng"
  value       = module.app_service_account.email
}
