package com.example.upload_service.dto;

import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UploadResponse {
    private String documentId;
    private String fileName;
    private long fileSize;
    private String fileType;
    private String uploadStatus;
    private String ingestionStatus;
    private String fileUrl;
}
