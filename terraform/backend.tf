terraform {
  backend "gcs" {
    # Thay đổi bucket này thành [gcp-project-id]-tfstate của bạn (phải tạo trước trên GCP Console)
    bucket = "legal-chatbot-496302"
    prefix = "terraform/state"
  }
}
