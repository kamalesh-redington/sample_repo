from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class SentenceTransformerEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing SentenceTransformerEmbedder")

        logger.debug(f"SentenceTransformer model: {config.model}")

        logger.debug(f"Batch size: {config.batch_size}")

        logger.debug(f"Normalize embeddings: {config.normalize}")

        try:

            from sentence_transformers import SentenceTransformer

        except ImportError as exc:

            logger.exception("sentence-transformers import failed")

            raise ImportError(
                "sentence-transformers required → pip install sentence-transformers"
            ) from exc

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            config.model,
            device=config.extra.get("device", "cpu"),
            cache_folder=config.extra.get("cache_dir"),
        )

        logger.info("SentenceTransformer model loaded successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(
                f"Starting SentenceTransformer embeddings for {len(texts)} text(s)"
            )

            vectors = self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize,
                show_progress_bar=False,
            )

            logger.info("SentenceTransformer embedding generation completed")

            logger.debug(f"Generated vectors count: {len(vectors)}")

            return vectors.tolist()

        except Exception as e:

            logger.exception("SentenceTransformer embedding generation failed")

            raise
