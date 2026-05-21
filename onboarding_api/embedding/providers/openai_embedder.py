from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class OpenAIEmbedder(BaseEmbedder):
    """Dense text embedder backed by the OpenAI Embeddings API."""

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing OpenAIEmbedder")

        logger.debug(f"OpenAI model configured: {config.model}")

        logger.debug(f"Embedding dimensions: {config.dimensions}")

        logger.debug(f"Batch size configured: {config.batch_size}")

        try:
            from openai import OpenAI

        except ImportError as exc:

            logger.exception("OpenAI package import failed")

            raise ImportError(
                "openai package is required → pip install openai"
            ) from exc

        self._client = OpenAI(
            api_key=config.extra.get("api_key"),
        )

        logger.info("OpenAI client initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(
                f"Starting OpenAI embedding generation for {len(texts)} text(s)"
            )

            all_vectors: List[List[float]] = []

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing OpenAI embedding batch size: {len(batch)}")

                response = self._client.embeddings.create(
                    model=self.config.model,
                    input=batch,
                    dimensions=(
                        self.config.dimensions
                        if "text-embedding-3" in self.config.model
                        else None
                    ),
                )

                logger.debug(f"OpenAI embeddings received: {len(response.data)}")

                for item in response.data:
                    all_vectors.append(item.embedding)

            logger.info("OpenAI embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("OpenAI embedding generation failed")

            raise
