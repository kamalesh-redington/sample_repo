"""
FastEmbed Dense Embedder
Provider key : "fastembed"
Embedding type: dense
Modality     : text

Optimized quantized ONNX inference (no GPU needed).

Popular models:
    - BAAI/bge-small-en-v1.5       (384-dim, very fast)
    - BAAI/bge-base-en-v1.5        (768-dim)
    - BAAI/bge-large-en-v1.5       (1024-dim)
    - sentence-transformers/all-MiniLM-L6-v2 (384-dim)

Extra config fields:
    cache_dir  : path to model cache directory
    threads    : number of ONNX inference threads
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class FastEmbedEmbedder(BaseEmbedder):
    """Dense text embedder backed by fastembed (ONNX quantized, CPU-optimised)."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise ImportError(
                "fastembed required → pip install fastembed"
            ) from exc

        from fastembed import TextEmbedding
        self._model = TextEmbedding(
            model_name=config.model,
            cache_dir=config.extra.get("cache_dir"),
            threads=config.extra.get("threads"),
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # fastembed returns a generator
        vectors = list(self._model.embed(
            documents=texts,
            batch_size=self.config.batch_size,
        ))
        return [v.tolist() for v in vectors]
