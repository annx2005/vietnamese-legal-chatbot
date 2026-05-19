variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "asia-southeast1"
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

variable "github_repo" {
  description = "GitHub Repository for Workload Identity Federation (format: owner/repo)"
  type        = string
}
