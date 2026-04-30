resource "google_storage_bucket" "bucket" {
  name          = var.bucket_name
  location      = var.location
  force_destroy = true # Cho phép xóa bucket kể cả khi có file (hữu ích cho Dev/Test)

  uniform_bucket_level_access = true
}
