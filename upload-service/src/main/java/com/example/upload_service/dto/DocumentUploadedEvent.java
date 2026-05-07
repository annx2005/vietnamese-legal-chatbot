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
    private String fileName;
    private String originalFileName;
    private String gcsUrl;
    private long sizeBytes;
    private String contentType;
    private long uploadedAtEpoch;
}
