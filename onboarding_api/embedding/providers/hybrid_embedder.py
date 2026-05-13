"""
Hybrid Embedder (Dense + Sparse fusion)
Provider key  : "hybrid"
Embedding type: hybrid
Modality      : text

Combines a dense embedder + a sparse embedder to support:
    - Pinecone hybrid search (upsert with both dense + sparse vectors)
    - Weaviate hybrid search
    - Any custom hybrid retrieval pipeline

Config (nested under embedding.hybrid):
    dense_provider  : "openai"
    dense_model     : "text-embedding-3-small"
    sparse_provider : "splade" | "bm25"
    sparse_model    : "naver/splade-cocondenser-ensembledistil"
    alpha           : 0.75     # weight for dense  (1-alpha = sparse weight)
"""
from typing import Any, Dict, List, Tuple

from embedding.base import BaseEmbedder, EmbeddingConfig


class HybridEmbedder(BaseEmbedder):
    """
    Wraps a dense and a sparse sub-embedder.

    embed_texts() returns the dense vector (for standard vector-DB upserts).
    embed_hybrid() returns (dense_vec, sparse_dict) tuples for hybrid search.
    """

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)

        # Lazy import to avoid circular dependency
        from embedding.factory import EmbeddingFactory

        dense_cfg_dict = {
            "embedding": {
                "provider": config.extra.get("dense_provider", "openai"),
                "model": config.extra.get("dense_model", "text-embedding-3-small"),
                "type": "dense",
                "dimensions": config.dimensions,
                "batch_size": config.batch_size,
                "normalize": config.normalize,
            }
        }
        sparse_cfg_dict = {
            "embedding": {
                "provider": config.extra.get("sparse_provider", "splade"),
                "model": config.extra.get(
                    "sparse_model",
                    "naver/splade-cocondenser-ensembledistil",
                ),
                "type": "sparse",
                "batch_size": config.batch_size,
            }
        }

        self._dense = EmbeddingFactory.create(dense_cfg_dict)
        self._sparse = EmbeddingFactory.create(sparse_cfg_dict)
        self._alpha: float = config.extra.get("alpha", 0.75)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Returns dense vectors only (backwards-compatible interface)."""
        return self._dense.embed_texts(texts)

    def embed_hybrid(
        self, texts: List[str]
    ) -> List[Tuple[List[float], Dict[int, float]]]:
        """
        Returns list of (dense_vector, sparse_dict) for each text.
        Suitable for direct upsert to Pinecone / Weaviate hybrid index.
        """
        dense_vecs = self._dense.embed_texts(texts)

        # Try to use sparse dict if the sparse embedder supports it
        if hasattr(self._sparse, "to_sparse_dicts"):
            sparse_dicts = self._sparse.to_sparse_dicts(texts)
        else:
            raw = self._sparse.embed_texts(texts)
            sparse_dicts = [
                {i: v for i, v in enumerate(vec) if v > 0}
                for vec in raw
            ]

        return list(zip(dense_vecs, sparse_dicts))
