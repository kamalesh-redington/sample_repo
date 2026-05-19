"""
Sentence Transformers Dense Embedder
Provider key : "sentence_transformers"
Embedding type: dense
Modality     : text

Popular models:
    - all-MiniLM-L6-v2          (384-dim, very fast)
    - all-mpnet-base-v2          (768-dim, balanced)
    - multi-qa-mpnet-base-dot-v1 (768-dim, QA optimised)
    - paraphrase-multilingual-MiniLM-L12-v2 (384-dim, multilingual)

Extra config fields:
    device     : "cpu" | "cuda" | "mps"
    cache_dir  : path to model cache directory
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class SentenceTransformerEmbedder(BaseEmbedder):
    """Dense text embedder using sentence-transformers library (runs locally)."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers required → pip install sentence-transformers"
            ) from exc

        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(
            config.model,
            device=config.extra.get("device", "cpu"),
            cache_folder=config.extra.get("cache_dir"),
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize,
            show_progress_bar=False,
        )
        return vectors.tolist()
