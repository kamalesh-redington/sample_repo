from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import Any, Dict, List, Tuple

from embedding.base import BaseEmbedder, EmbeddingConfig


class HybridEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing HybridEmbedder")

        logger.debug(f"Hybrid alpha value: {config.extra.get('alpha', 0.75)}")

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

        logger.info("Creating dense embedder for hybrid pipeline")

        self._dense = EmbeddingFactory.create(dense_cfg_dict)

        logger.info("Creating sparse embedder for hybrid pipeline")

        self._sparse = EmbeddingFactory.create(sparse_cfg_dict)

        self._alpha: float = config.extra.get("alpha", 0.75)

        logger.info("Hybrid embedder initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Generating hybrid dense embeddings for {len(texts)} text(s)")

            vectors = self._dense.embed_texts(texts)

            logger.debug(f"Generated dense vectors count: {len(vectors)}")

            return vectors

        except Exception as e:

            logger.exception("Hybrid dense embedding generation failed")

            raise

    def embed_hybrid(
        self, texts: List[str]
    ) -> List[Tuple[List[float], Dict[int, float]]]:

        try:

            logger.info(f"Generating full hybrid embeddings for {len(texts)} text(s)")

            dense_vecs = self._dense.embed_texts(texts)

            logger.debug(f"Dense vectors generated: {len(dense_vecs)}")

            if hasattr(self._sparse, "to_sparse_dicts"):

                logger.info("Using sparse dictionary conversion")

                sparse_dicts = self._sparse.to_sparse_dicts(texts)

            else:

                logger.warning(
                    "Sparse embedder lacks sparse dict support, using fallback conversion"
                )

                raw = self._sparse.embed_texts(texts)

                sparse_dicts = [
                    {i: v for i, v in enumerate(vec) if v > 0} for vec in raw
                ]

            logger.debug(f"Sparse vectors generated: {len(sparse_dicts)}")

            logger.info("Hybrid embedding generation completed successfully")

            return list(zip(dense_vecs, sparse_dicts))

        except Exception as e:

            logger.exception("Hybrid embedding generation failed")

            raise
