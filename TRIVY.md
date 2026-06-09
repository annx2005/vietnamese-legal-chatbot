# Trivy

Repo này dùng Trivy để scan bảo mật trong GitHub Actions.

Workflow:

```text
.github/workflows/trivy.yml
```

Workflow chạy khi push/PR vào `main` hoặc bấm `Run workflow`.

## Scan những gì

- Filesystem/dependency/IaC: `vuln`, `secret`, `misconfig`.
- Docker images: build từng service rồi scan `vuln`, `secret`.
- Severity chặn CI: `HIGH,CRITICAL`.
- `ignore-unfixed: true` để giảm nhiễu từ CVE chưa có bản vá.

Kết quả SARIF được upload vào GitHub Code Scanning nếu repo hỗ trợ.

## Bắt buộc Trivy pass trước khi merge

Sau khi workflow chạy ít nhất một lần, vào GitHub repository:

```text
Settings -> Branches -> main rule
```

Bật required status checks:

```text
Trivy Security Scan / Scan Filesystem and IaC
Trivy Security Scan / Scan Image (frontend)
Trivy Security Scan / Scan Image (api-router)
Trivy Security Scan / Scan Image (auth-service)
Trivy Security Scan / Scan Image (upload-service)
Trivy Security Scan / Scan Image (rag-service)
Trivy Security Scan / Scan Image (ingestion-service)
```

Khi đó PR chỉ merge được nếu Trivy pass.

## Ghi chú bảo mật

`aquasecurity/trivy-action` được pin bằng commit SHA của tag `v0.36.0`:

```text
a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8
```

Không dùng `@master` hoặc tag trôi để giảm rủi ro supply-chain trong GitHub Actions.
