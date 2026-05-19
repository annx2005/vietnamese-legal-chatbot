variable "bucket_name" {
  description = "Tên của bucket (phải là unique trên toàn cầu)"
  type        = string
}

variable "location" {
  description = "Vị trí đặt bucket"
  type        = string
  default     = "asia-southeast1"
}
