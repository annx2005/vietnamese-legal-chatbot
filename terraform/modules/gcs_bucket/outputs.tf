output "bucket_name" {
  description = "Tên của bucket đã được tạo"
  value       = google_storage_bucket.bucket.name
}

output "bucket_url" {
  description = "URL của bucket"
  value       = google_storage_bucket.bucket.url
}
