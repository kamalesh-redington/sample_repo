"""
Voyage AI Dense Embedder
Provider key : "voyage"
Embedding type: dense
Modality     : text

Supported models:
    - voyage-3-large           (1024-dim, strongest)
    - voyage-3                 (1024-dim, balanced)
    - voyage-3-lite            (512-dim, fast)
    - voyage-code-3            (1024-dim, code)
    - voyage-finance-2         (1024-dim, finance domain)
    - voyage-law-2             (1024-dim, legal domain)

Extra config fields:
    api_key    : Voyage API key (or env VOYAGE_API_KEY)
    input_type : "document" | "query"  (default: "document")
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class VoyageEmbedder(BaseEmbedder):
    """Dense text embedder backed by Voyage AI — highly optimized for retrieval."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import voyageai
        except ImportError as exc:
            raise ImportError(
                "voyageai package is required → pip install voyageai"
            ) from exc

        self._client = voyageai.Client(api_key=config.extra.get("api_key"))
        self._input_type = config.extra.get("input_type", "document")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            result = self._client.embed(
                texts=batch,
                model=self.config.model,
                input_type=self._input_type,
                output_dimension=self.config.dimensions or None,
            )
            all_vectors.extend(result.embeddings)

        return all_vectors
