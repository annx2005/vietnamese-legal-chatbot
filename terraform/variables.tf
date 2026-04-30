variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (e.g., prod)"
  type        = string
  default     = "prod"
}

variable "bucket_name" {
  description = "Name of the GCS bucket for document uploads"
  type        = string
}
