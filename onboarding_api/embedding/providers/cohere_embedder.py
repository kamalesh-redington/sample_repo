from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class CohereEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info(
            "Initializing CohereEmbedder"
        )

        logger.debug(
            f"Cohere model configured: {config.model}"
        )

        try:

            import cohere

        except ImportError as exc:

            logger.exception(
                "Cohere import failed"
            )

            raise ImportError(
                "cohere package is required → pip install cohere"
            ) from exc

        self._client = cohere.Client(
            api_key=config.extra.get("api_key")
        )

        self._input_type = config.extra.get(
            "input_type",
            "search_document"
        )

        logger.info(
            "Cohere client initialized successfully"
        )

    def embed_texts(
        self,
        texts: List[str]
    ) -> List[List[float]]:

        try:

            logger.info(
                f"Starting Cohere embeddings for {len(texts)} text(s)"
            )

            all_vectors: List[List[float]] = []

            for i in range(
                0,
                len(texts),
                self.config.batch_size
            ):

                batch = texts[
                    i : i + self.config.batch_size
                ]

                logger.debug(
                    f"Processing Cohere batch size: {len(batch)}"
                )

                response = self._client.embed(
                    texts=batch,
                    model=self.config.model,
                    input_type=self._input_type,
                )

                all_vectors.extend(
                    response.embeddings
                )

            logger.info(
                "Cohere embedding generation completed successfully"
            )

            logger.debug(
                f"Generated vectors count: {len(all_vectors)}"
            )

            return all_vectors

        except Exception as e:

            logger.exception(
                "Cohere embedding generation failed"
            )

            raise