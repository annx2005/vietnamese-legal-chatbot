from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Service API"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    COLLECTION_NAME: str = "legal_documents"
    EMBEDDING_MODEL_NAME: str = "textembedding-gecko@003"
    LLM_MODEL_NAME: str = "gemini-1.5-pro-preview-0409"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
