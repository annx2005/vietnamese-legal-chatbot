package com.example.upload_service.service;

import com.example.upload_service.dto.UploadResponse;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@Service
public class UploadService {

    public UploadResponse uploadFile(MultipartFile file) {
        if (file.isEmpty()) {
            throw new RuntimeException("Cannot upload empty file");
        }

        // Placeholder logic: in production, save to GCS bucket using Google Cloud Storage SDK
        String generatedFileName = UUID.randomUUID().toString() + "_" + file.getOriginalFilename();

        return UploadResponse.builder()
                .fileName(file.getOriginalFilename())
                .fileSize(file.getSize())
                .fileType(file.getContentType())
                .uploadStatus("SUCCESS")
                .fileUrl("https://storage.googleapis.com/placeholder-bucket/" + generatedFileName)
                .build();
    }
}
