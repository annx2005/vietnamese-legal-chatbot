output "email" {
  description = "Địa chỉ email của service account"
  value       = google_service_account.sa.email
}

output "name" {
  description = "Tên đầy đủ của resource service account"
  value       = google_service_account.sa.name
}
