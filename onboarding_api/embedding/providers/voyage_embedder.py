from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class VoyageEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing VoyageEmbedder")

        logger.debug(f"Voyage model configured: {config.model}")

        try:

            import voyageai

        except ImportError as exc:

            logger.exception("voyageai import failed")

            raise ImportError("voyageai required → pip install voyageai") from exc

        self._client = voyageai.Client(api_key=config.extra.get("api_key"))

        logger.info("Voyage client initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting Voyage embeddings for {len(texts)} text(s)")

            all_vectors: List[List[float]] = []

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing Voyage batch size: {len(batch)}")

                response = self._client.embed(batch, model=self.config.model)

                all_vectors.extend(response.embeddings)

            logger.info("Voyage embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("Voyage embedding generation failed")

            raise
