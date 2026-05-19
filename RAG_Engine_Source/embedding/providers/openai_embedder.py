"""
OpenAI Dense Embedder
Provider key : "openai"
Embedding type: dense
Modality     : text

Supports:
    - text-embedding-3-small  (1536-dim)
    - text-embedding-3-large  (3072-dim)
    - text-embedding-ada-002  (legacy, 1536-dim)
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class OpenAIEmbedder(BaseEmbedder):
    """Dense text embedder backed by the OpenAI Embeddings API."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is required → pip install openai"
            ) from exc

        self._client = OpenAI(
            api_key=config.extra.get("api_key"),          # falls back to OPENAI_API_KEY env
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []

        # batch the calls
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            response = self._client.embeddings.create(
                model=self.config.model,
                input=batch,
                dimensions=self.config.dimensions
                if "text-embedding-3" in self.config.model
                else None,
            )
            for item in response.data:
                all_vectors.append(item.embedding)

        return all_vectors
