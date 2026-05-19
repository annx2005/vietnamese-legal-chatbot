package com.example.upload_service.service;

import com.example.upload_service.dto.DocumentUploadedEvent;
import com.example.upload_service.dto.UploadResponse;
import com.google.cloud.pubsub.v1.Publisher;
import com.google.cloud.storage.BlobId;
import com.google.cloud.storage.BlobInfo;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageOptions;
import com.google.gson.Gson;
import com.google.protobuf.ByteString;
import com.google.pubsub.v1.PubsubMessage;
import com.google.pubsub.v1.TopicName;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.ExecutionException;

@Slf4j
@Service
public class UploadService {

    @Value("${spring.cloud.gcp.project-id}")
    private String projectId;

    @Value("${spring.cloud.gcp.storage.bucket}")
    private String bucketName;

    @Value("${spring.cloud.gcp.pubsub.topic}")
    private String topicId;

    private Storage storage;
    private Publisher publisher;
    private final Gson gson = new Gson();

    @PostConstruct
    public void init() {
        try {
            // Initialize GCS client
            this.storage = StorageOptions.newBuilder().setProjectId(projectId).build().getService();
            log.info("Initialized Google Cloud Storage client for project: {}", projectId);

            // Initialize Pub/Sub Publisher
            TopicName topicName = TopicName.of(projectId, topicId);
            this.publisher = Publisher.newBuilder(topicName).build();
            log.info("Initialized Google Cloud Pub/Sub publisher for topic: {}", topicName.toString());
        } catch (IOException e) {
            log.error("Failed to initialize GCP clients", e);
            throw new RuntimeException("Could not initialize GCP clients", e);
        }
    }

    @PreDestroy
    public void cleanup() {
        if (publisher != null) {
            publisher.shutdown();
        }
    }

    public UploadResponse uploadFile(MultipartFile file) {
        if (file.isEmpty()) {
            throw new RuntimeException("Cannot upload empty file");
        }

        // 1. Validate file extension
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || !originalFilename.toLowerCase().endsWith(".pdf")) {
            throw new RuntimeException("Only PDF files are allowed");
        }

        try {
            // 2. Upload to Google Cloud Storage
            String documentId = "doc_" + UUID.randomUUID().toString().replace("-", "");
            String generatedFileName = documentId + "_" + originalFilename;
            BlobId blobId = BlobId.of(bucketName, generatedFileName);
            BlobInfo blobInfo = BlobInfo.newBuilder(blobId)
                    .setContentType(file.getContentType())
                    .build();
            
            log.info("Uploading file {} to bucket {}", generatedFileName, bucketName);
            storage.create(blobInfo, file.getBytes());
            
            String gcsUrl = String.format("gs://%s/%s", bucketName, generatedFileName);
            log.info("Successfully uploaded file to {}", gcsUrl);

            // 3. Publish message to Pub/Sub
            DocumentUploadedEvent event = DocumentUploadedEvent.builder()
                    .fileName(generatedFileName)
                    .originalFileName(originalFilename)
                    .gcsUrl(gcsUrl)
                    .sizeBytes(file.getSize())
                    .contentType(file.getContentType())
                    .uploadedAtEpoch(Instant.now().toEpochMilli())
                    .build();
            
            String eventJson = gson.toJson(event);
            ByteString data = ByteString.copyFromUtf8(eventJson);
            PubsubMessage pubsubMessage = PubsubMessage.newBuilder()
                    .setData(data)
                    .build();
            
            publisher.publish(pubsubMessage).get(); // Block until published
            log.info("Published DocumentUploadedEvent to topic {}", topicId);

            // 4. Return response
            return UploadResponse.builder()
                    .documentId(documentId)
                    .fileName(originalFilename)
                    .fileSize(file.getSize())
                    .fileType(file.getContentType())
                    .uploadStatus("SUCCESS")
                    .ingestionStatus("QUEUED")
                    .fileUrl(gcsUrl)
                    .build();

        } catch (IOException | InterruptedException | ExecutionException e) {
            log.error("Error during file upload and event publishing", e);
            throw new RuntimeException("Failed to process file upload", e);
        }
    }
}
