variable "bucket_name" {
  description = "Tên của bucket cần cấp quyền"
  type        = string
}

variable "role" {
  description = "Quyền (Role) cần cấp (ví dụ: roles/storage.objectAdmin)"
  type        = string
}

variable "service_account_email" {
  description = "Email của Service Account được cấp quyền"
  type        = string
}
