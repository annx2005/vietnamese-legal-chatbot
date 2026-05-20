package com.example.upload_service.service;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class DocumentPersistenceService {

    private static final String CREATE_DOCUMENTS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS documents (
                document_id VARCHAR(64) PRIMARY KEY,
                title VARCHAR(512) NOT NULL,
                source_url TEXT NOT NULL,
                document_type VARCHAR(32) NOT NULL DEFAULT 'PDF',
                domain VARCHAR(128) NOT NULL DEFAULT 'general',
                effective_status VARCHAR(64) NOT NULL DEFAULT 'unknown',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                chunks_count INTEGER NOT NULL DEFAULT 0,
                ingestion_status VARCHAR(32) NOT NULL DEFAULT 'queued',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """;

    private static final String UPSERT_DOCUMENT_SQL = """
            INSERT INTO documents (
                document_id, title, source_url, document_type, domain, effective_status,
                enabled, chunks_count, ingestion_status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'general', 'unknown', TRUE, 0, 'queued', NOW(), NOW())
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                source_url = EXCLUDED.source_url,
                document_type = EXCLUDED.document_type,
                enabled = TRUE,
                ingestion_status = 'queued',
                updated_at = NOW()
            """;

    private final JdbcTemplate jdbcTemplate;

    @PostConstruct
    void ensureDocumentsTable() {
        jdbcTemplate.execute(CREATE_DOCUMENTS_TABLE_SQL);
    }

    public void upsertUploadedDocument(String documentId, String title, String sourceUrl, String documentType) {
        jdbcTemplate.update(
                UPSERT_DOCUMENT_SQL,
                documentId,
                title,
                sourceUrl,
                documentType
        );
    }
}
