from typing import List

import vertexai
from app.core.config import settings
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel


class VertexAIService:
    def __init__(self) -> None:
        self._initialized = False
        self._embedding_model: TextEmbeddingModel | None = None

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        self._initialized = True

    def _ensure_embedding_model(self) -> TextEmbeddingModel:
        self._ensure_initialized()
        if self._embedding_model is None:
            self._embedding_model = TextEmbeddingModel.from_pretrained(settings.EMBEDDING_MODEL_NAME)
        return self._embedding_model

    def _build_generative_model(self, system_prompt: str) -> GenerativeModel:
        self._ensure_initialized()
        return GenerativeModel(
            settings.LLM_MODEL_NAME,
            system_instruction=[system_prompt],
        )

    def embed_query(self, text: str) -> List[float]:
        model = self._ensure_embedding_model()
        embedding = model.get_embeddings(
            [text],
            output_dimensionality=settings.VECTOR_SIZE,
        )[0]
        return list(embedding.values)

    def generate_answer(self, *, system_prompt: str, user_prompt: str) -> str:
        model = self._build_generative_model(system_prompt)
        response = model.generate_content(
            user_prompt,
            generation_config={
                "temperature": settings.LLM_TEMPERATURE,
                "max_output_tokens": settings.LLM_MAX_OUTPUT_TOKENS,
            },
        )
        if getattr(response, "text", ""):
            return response.text.strip()
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            texts = [getattr(part, "text", "").strip() for part in parts if getattr(part, "text", "")]
            if texts:
                return "\n".join(texts).strip()
        raise RuntimeError("Vertex AI returned an empty response")
