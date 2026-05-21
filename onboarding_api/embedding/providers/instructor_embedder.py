from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class InstructorEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing InstructorEmbedder")

        logger.debug(f"Instructor model configured: {config.model}")

        try:

            from InstructorEmbedding import INSTRUCTOR

        except ImportError as exc:

            logger.exception("InstructorEmbedding import failed")

            raise ImportError(
                "InstructorEmbedding required → pip install InstructorEmbedding"
            ) from exc

        from InstructorEmbedding import INSTRUCTOR

        self._model = INSTRUCTOR(config.model)

        self._instruction = config.extra.get(
            "instruction", "Represent the document for retrieval:"
        )

        logger.info("Instructor model initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting Instructor embeddings for {len(texts)} text(s)")

            pairs = [[self._instruction, text] for text in texts]

            logger.debug(f"Prepared instruction-text pairs: {len(pairs)}")

            vectors = self._model.encode(pairs)

            logger.info("Instructor embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(vectors)}")

            return vectors.tolist()

        except Exception as e:

            logger.exception("Instructor embedding generation failed")

            raise
