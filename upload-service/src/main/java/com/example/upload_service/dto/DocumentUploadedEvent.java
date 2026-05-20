package com.example.upload_service.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentUploadedEvent {
    private String documentId;
    private String fileName;
    private String originalFileName;
    private String gcsUrl;
    private String documentType;
    private long sizeBytes;
    private String contentType;
    private long uploadedAtEpoch;
}
