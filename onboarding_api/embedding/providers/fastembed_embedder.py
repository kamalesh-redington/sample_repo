from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class FastEmbedEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing FastEmbedEmbedder")

        logger.debug(f"FastEmbed model configured: {config.model}")

        try:

            from fastembed import TextEmbedding

        except ImportError as exc:

            logger.exception("fastembed import failed")

            raise ImportError("fastembed required → pip install fastembed") from exc

        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=config.model)

        logger.info("FastEmbed model initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting FastEmbed embeddings for {len(texts)} text(s)")

            embeddings = list(self._model.embed(texts))

            logger.info("FastEmbed embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(embeddings)}")

            return [emb.tolist() for emb in embeddings]

        except Exception as e:

            logger.exception("FastEmbed embedding generation failed")

            raise
