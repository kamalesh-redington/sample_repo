"""
Google Vertex AI Embedder
Provider key : "google"
Embedding type: dense
Modality     : text | multimodal

Supported models:
    - text-embedding-004            (768-dim)
    - textembedding-gecko@003       (768-dim, legacy)
    - multimodalembedding@001       (1408-dim, text+image)

Extra config fields:
    project  : GCP project ID
    location : "us-central1"
    task_type: "RETRIEVAL_DOCUMENT" | "RETRIEVAL_QUERY" | "SEMANTIC_SIMILARITY"
"""

from typing import List, Optional

from embedding.base import BaseEmbedder, EmbeddingConfig


class GoogleVertexEmbedder(BaseEmbedder):
    """Dense / multimodal embedder backed by Google Vertex AI."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from google.cloud import aiplatform
            from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
        except ImportError as exc:
            raise ImportError(
                "google-cloud-aiplatform is required → pip install google-cloud-aiplatform"
            ) from exc

        aiplatform.init(
            project=config.extra.get("project"),
            location=config.extra.get("location", "us-central1"),
        )
        from vertexai.language_models import TextEmbeddingModel
        self._model = TextEmbeddingModel.from_pretrained(config.model)
        self._TextEmbeddingInput = TextEmbeddingInput
        self._task_type = config.extra.get("task_type", "RETRIEVAL_DOCUMENT")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        from vertexai.language_models import TextEmbeddingInput

        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            inputs = [TextEmbeddingInput(t, self._task_type) for t in batch]
            embeddings = self._model.get_embeddings(
                inputs,
                output_dimensionality=self.config.dimensions or None,
            )
            for emb in embeddings:
                all_vectors.append(emb.values)

        return all_vectors
