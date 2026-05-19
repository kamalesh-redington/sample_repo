"""
Cohere Dense Embedder
Provider key : "cohere"
Embedding type: dense
Modality     : text | multimodal (embed-v3)

Supported models:
    - embed-english-v3.0           (1024-dim)
    - embed-multilingual-v3.0      (1024-dim)
    - embed-english-light-v3.0     (384-dim)

Extra config fields:
    api_key      : Cohere API key (or env COHERE_API_KEY)
    input_type   : "search_document" | "search_query" | "classification" | "clustering"
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class CohereEmbedder(BaseEmbedder):
    """Dense text embedder backed by Cohere's Embed API (v3)."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import cohere
        except ImportError as exc:
            raise ImportError(
                "cohere package is required → pip install cohere"
            ) from exc

        self._client = cohere.Client(api_key=config.extra.get("api_key"))
        self._input_type = config.extra.get("input_type", "search_document")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            response = self._client.embed(
                texts=batch,
                model=self.config.model,
                input_type=self._input_type,
            )
            all_vectors.extend(response.embeddings)

        return all_vectors
