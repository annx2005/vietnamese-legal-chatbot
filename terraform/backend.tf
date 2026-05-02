terraform {
  backend "gcs" {
    # Thay đổi bucket này thành [gcp-project-id]-tfstate của bạn (phải tạo trước trên GCP Console)
    bucket = "legal-rag-tfstate-bucket"
    prefix = "terraform/state"
  }
}
