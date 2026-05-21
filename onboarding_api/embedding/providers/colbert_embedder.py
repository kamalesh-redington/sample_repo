from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class ColBERTEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing ColBERTEmbedder")

        logger.debug(f"ColBERT model configured: {config.model}")

        try:

            from sentence_transformers import SentenceTransformer

        except ImportError as exc:

            logger.exception("sentence-transformers import failed")

            raise ImportError(
                "sentence-transformers required → pip install sentence-transformers"
            ) from exc

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(config.model)

        logger.info("ColBERT model initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting ColBERT embeddings for {len(texts)} text(s)")

            vectors = self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize,
                show_progress_bar=False,
            )

            logger.info("ColBERT embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(vectors)}")

            return vectors.tolist()

        except Exception as e:

            logger.exception("ColBERT embedding generation failed")

            raise
