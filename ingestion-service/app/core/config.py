from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ingestion Service API"
    GCP_PROJECT_ID: str = "legal-rag-project"
    GCP_LOCATION: str = "asia-southeast1"
    PUBSUB_TOPIC: str = "document-ingestion-topic"
    GCS_BUCKET_NAME: str = "legal-documents-storage"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    COLLECTION_NAME: str = "legal_documents"
    EMBEDDING_MODEL_NAME: str = "text-embedding-005"
    VECTOR_SIZE: int = 384
    VERTEX_EMBEDDING_BATCH_SIZE: int = 8
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 160
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-in-production"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
