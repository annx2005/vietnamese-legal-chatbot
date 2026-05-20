# 🔐 Quy Ước Quản Lý Hạ Tầng, Biến Môi Trường & Secrets (Terraform & GCP)

Tài liệu này xác định các quy ước chuẩn cho đội ngũ **2 Dev** trong việc lưu trữ Trạng thái Hạ tầng (Remote State), khóa trạng thái (State Locking) và quản lý thông tin bảo mật (Secrets / Biến môi trường) để đảm bảo an toàn tối đa cho hệ thống.

---

## ☁️ 1. Cơ Chế Remote State & State Locking (GCS Backend)

### 📌 Tại sao cần Remote State & State Locking?
*   **Remote State:** Khi có nhiều hơn 1 nhà phát triển cùng làm việc, file cấu hình trạng thái hạ tầng (`terraform.tfstate`) được lưu tập trung trên **Google Cloud Storage (GCS)** thay vì máy cá nhân, đảm bảo tất cả các dev đều nhìn thấy cùng một trạng thái hạ tầng hiện tại.
*   **State Locking:** Khi Dev 2 đang chạy `terraform apply`, Terraform sẽ tự động khóa (Lock) file trạng thái trên GCS. Nếu Dev 1 cũng chạy lệnh apply vào cùng thời điểm, yêu cầu của Dev 1 sẽ bị chặn lại để tránh xung đột làm hỏng hạ tầng.

### 🛠️ Quy trình thiết lập:
1.  **Tạo Bucket chứa State (Thủ công trên GCP Console hoặc qua gcloud CLI):**
    *   Tên bucket nên tuân theo định dạng: `[gcp-project-id]-tfstate` (Ví dụ: `legal-rag-chatbot-project-tfstate`).
    *   Vùng lưu trữ: Chọn cùng region với hạ tầng của bạn (Ví dụ: `asia-southeast1`).
2.  **Cấu hình trong file [backend.tf](file:///Users/annx/Projects/legal-rag-chatbot/terraform/backend.tf):**
    ```hcl
    terraform {
      backend "gcs" {
        bucket = "legal-rag-chatbot-project-tfstate" # Thay bằng tên bucket của bạn
        prefix = "terraform/state"
      }
    }
    ```
3.  **Khởi chạy (Init):** Chạy `terraform init`. Terraform sẽ tự động cấu hình backend GCS và kích hoạt tính năng khóa trạng thái tự động.

---

## 🔑 2. Quy Ước Quản Lý Biến Môi Trường & Secrets

Để tránh rò rỉ thông tin bảo mật, chúng ta phân chia secrets làm 3 cấp độ:

### 🅰️ Cấp Độ 1: Cấu hình Hạ Tầng (Terraform)
*   **File `terraform.tfvars`:** 
    *   Được dùng để định nghĩa các giá trị thực tế cho local (`project_id`, `bucket_name`, v.v.).
    *   **Quy tắc:** Tuyệt đối **KHÔNG** commit file `terraform.tfvars` lên Git (Đã được chặn tự động bởi `.gitignore`).
    *   Mỗi nhà phát triển tự copy file `terraform.tfvars.example` sang `terraform.tfvars` tại máy local để làm việc.
*   **Khai báo biến nhạy cảm (Secrets):**
    *   Nếu có biến nhạy cảm (như mật khẩu cơ sở dữ liệu), hãy khai báo trong `variables.tf` với thuộc tính `sensitive = true` để tránh bị in ra màn hình log:
        ```hcl
        variable "db_password" {
          type      = string
          sensitive = true
        }
        ```
    *   Các biến nhạy cảm này có thể được truyền vào qua biến môi trường của hệ điều hành với tiền tố `TF_VAR_`:
        ```bash
        export TF_VAR_db_password="mat-khau-sieu-bao-mat"
        ```

### 🅱️ Cấp Độ 2: Môi Trường Phát Triển Local (Docker Compose)
*   **File `.env` ở thư mục gốc:**
    *   Chứa tất cả cấu hình chạy thử của các microservices (`api-router`, PostgreSQL, Qdrant).
    *   **Quy tắc:** Chỉ được commit file `.env.example` chứa các cấu hình mẫu lên GitHub. File `.env` thực tế sẽ bị bỏ qua (đã có trong `.gitignore`).

### 🆃 Cấp Độ 3: Môi Trường Triển Khai Thực Tế (GCP Production)
*   **GCP Secret Manager:**
    *   Mọi thông tin bảo mật cao (chìa khóa API, mật khẩu Database Production, JWT Secret Key) sẽ được khởi tạo trực tiếp trên **GCP Secret Manager**.
    *   Các microservices chạy trên Cloud Run hoặc GKE sẽ đọc secrets trực tiếp từ GCP Secret Manager khi khởi chạy thông qua quyền hạn của Service Account, không lưu trực tiếp vào Docker Image hay cấu hình cứng.

---

## 🚨 Quy Tắc Vàng Cho Dev 1 & Dev 2:

> [!WARNING]
> 1. Không bao giờ lưu file JSON Key Service Account vào trong thư mục dự án.
> 2. Luôn kiểm tra kỹ bằng lệnh `git status` để đảm bảo không vô tình commit file `.env`, `terraform.tfvars`, hay file `*.json` chứa khóa bảo mật.
> 3. Khi viết thêm biến mới vào Terraform, luôn cập nhật file `variables.tf` và bổ sung biến mẫu vào `terraform.tfvars.example`.
