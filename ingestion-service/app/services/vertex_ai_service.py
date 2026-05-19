from typing import List

import vertexai
from app.core.config import settings
from vertexai.language_models import TextEmbeddingModel


class VertexAIEmbeddingService:
    def __init__(self) -> None:
        self._initialized = False
        self._model: TextEmbeddingModel | None = None

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        self._initialized = True

    def _ensure_model(self) -> TextEmbeddingModel:
        self._ensure_initialized()
        if self._model is None:
            self._model = TextEmbeddingModel.from_pretrained(settings.EMBEDDING_MODEL_NAME)
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        embeddings = model.get_embeddings(
            texts,
            output_dimensionality=settings.VECTOR_SIZE,
        )
        return [list(item.values) for item in embeddings]
