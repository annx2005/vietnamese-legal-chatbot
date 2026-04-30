resource "google_storage_bucket_iam_member" "binding" {
  bucket = var.bucket_name
  role   = var.role
  member = "serviceAccount:${var.service_account_email}"
}
