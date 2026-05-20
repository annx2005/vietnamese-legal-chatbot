from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Service API"
    GCP_PROJECT_ID: str = "legal-rag-project"
    GCP_LOCATION: str = "asia-southeast1"
    QDRANT_URL: str = ""
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    LEGACY_QDRANT_URL: str = Field(default="", validation_alias="CLUSTER_ENDPOINT")
    LEGACY_QDRANT_API_KEY: str = Field(default="", validation_alias="CLOUD_QDRANT_API_KEY")
    COLLECTION_NAME: str = "legal_documents"
    EMBEDDING_MODEL_NAME: str = "text-embedding-005"
    LLM_MODEL_NAME: str = "gemini-2.5-flash"
    VECTOR_SIZE: int = 384
    CONFIDENCE_THRESHOLD: float = 0.18
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 1024
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-in-production"
    DEFAULT_DISCLAIMER: str = "Thông tin chỉ dùng để tham khảo, không thay thế tư vấn của luật sư hoặc cơ quan có thẩm quyền."
    SYSTEM_PROMPT_PATH: str = str(Path(__file__).resolve().parents[1] / "prompts" / "system_prompt.txt")
    USER_PROMPT_PATH: str = str(Path(__file__).resolve().parents[1] / "prompts" / "user_prompt.txt")
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
