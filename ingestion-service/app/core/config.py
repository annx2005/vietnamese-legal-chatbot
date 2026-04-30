from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ingestion Service API"
    GCP_PROJECT_ID: str = "legal-rag-project"
    PUBSUB_TOPIC: str = "document-ingestion-topic"
    GCS_BUCKET_NAME: str = "legal-documents-storage"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
