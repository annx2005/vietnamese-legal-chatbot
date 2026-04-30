terraform {
  backend "gcs" {
    # Thay đổi bucket này thành bucket chứa state thực tế của bạn
    # bucket  = "legal-rag-tfstate-bucket"
    # prefix  = "terraform/state"
  }
}
