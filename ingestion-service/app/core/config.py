from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ingestion Service API"
    GCP_PROJECT_ID: str = "legal-rag-project"
    GCP_LOCATION: str = "asia-southeast1"
    PUBSUB_TOPIC: str = "document-ingestion-topic"
    PUBSUB_SUBSCRIPTION: str = ""
    PUBSUB_WORKER_MAX_MESSAGES: int = 1
    GCS_BUCKET_NAME: str = "legal-documents-storage"
    QDRANT_URL: str = ""
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    LEGACY_QDRANT_URL: str = Field(default="", validation_alias="CLUSTER_ENDPOINT")
    LEGACY_QDRANT_API_KEY: str = Field(default="", validation_alias="CLOUD_QDRANT_API_KEY")
    COLLECTION_NAME: str = "legal_documents"
    EMBEDDING_MODEL_NAME: str = "text-embedding-005"
    VECTOR_SIZE: int = 384
    VERTEX_EMBEDDING_BATCH_SIZE: int = 8
    QDRANT_SPARSE_VECTOR_NAME: str = "bm25_sparse_vector"
    BM25_AVG_LEN: float = 0.0
    BM25_LANGUAGE: str = "none"
    BM25_TOKENIZER: str = "multilingual"
    BM25_ASCII_FOLDING: bool = True
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 160
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-in-production"
    DATABASE_URL: str | None = None
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "legal_rag_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    CLOUD_SQL_CONNECTION_NAME: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _normalize_qdrant_config(self) -> "Settings":
        if not self.QDRANT_URL and self.LEGACY_QDRANT_URL:
            self.QDRANT_URL = self.LEGACY_QDRANT_URL
        if (not self.QDRANT_API_KEY or self.QDRANT_API_KEY == "your-qdrant-api-key-here") and self.LEGACY_QDRANT_API_KEY:
            self.QDRANT_API_KEY = self.LEGACY_QDRANT_API_KEY
        return self

settings = Settings()
