from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class GoogleVertexEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing GoogleVertexEmbedder")

        logger.debug(f"Vertex model configured: {config.model}")

        try:

            import vertexai

        except ImportError as exc:

            logger.exception("vertexai import failed")

            raise ImportError(
                "vertexai required → pip install google-cloud-aiplatform"
            ) from exc

        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(
            project=config.extra.get("project"),
            location=config.extra.get("location", "us-central1"),
        )

        self._model = TextEmbeddingModel.from_pretrained(config.model)

        logger.info("Google Vertex model initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting Google Vertex embeddings for {len(texts)} text(s)")

            all_vectors: List[List[float]] = []

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing Vertex batch size: {len(batch)}")

                embeddings = self._model.get_embeddings(batch)

                all_vectors.extend([emb.values for emb in embeddings])

            logger.info("Google Vertex embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("Google Vertex embedding generation failed")

            raise
