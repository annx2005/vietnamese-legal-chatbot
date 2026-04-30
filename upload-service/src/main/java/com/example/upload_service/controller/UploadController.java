package com.example.upload_service.controller;

import com.example.upload_service.dto.UploadResponse;
import com.example.upload_service.service.UploadService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/files") // Mapped via context-path /api/v1/upload
@RequiredArgsConstructor
@Tag(name = "File Upload", description = "Endpoints for uploading legal documents (PDFs)")
public class UploadController {

    private final UploadService uploadService;

    @Operation(summary = "Upload a document file (PDF)")
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<UploadResponse> uploadFile(
            @Parameter(description = "File to upload", content = @Content(mediaType = MediaType.MULTIPART_FORM_DATA_VALUE))
            @RequestParam("file") MultipartFile file) {
        return ResponseEntity.ok(uploadService.uploadFile(file));
    }
}
