from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class AzureOpenAIEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing AzureOpenAIEmbedder")

        logger.debug(f"Azure OpenAI model configured: {config.model}")

        logger.debug(f"Embedding dimensions: {config.dimensions}")

        try:

            from openai import AzureOpenAI

        except ImportError as exc:

            logger.exception("Azure OpenAI import failed")

            raise ImportError("openai package required → pip install openai") from exc

        self._client = AzureOpenAI(
            api_key=config.extra.get("api_key"),
            api_version=config.extra.get("api_version", "2024-02-01"),
            azure_endpoint=config.extra.get("endpoint"),
        )

        logger.info("Azure OpenAI client initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting Azure OpenAI embeddings for {len(texts)} text(s)")

            all_vectors = []

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing Azure OpenAI batch size: {len(batch)}")

                response = self._client.embeddings.create(
                    model=self.config.model,
                    input=batch,
                    dimensions=self.config.dimensions,
                )

                for item in response.data:

                    all_vectors.append(item.embedding)

            logger.info("Azure OpenAI embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("Azure OpenAI embedding generation failed")

            raise
