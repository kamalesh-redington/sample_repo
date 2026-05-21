from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class OllamaEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing OllamaEmbedder")

        logger.debug(f"Ollama model configured: {config.model}")

        try:

            import requests

        except ImportError as exc:

            logger.exception("requests import failed")

            raise ImportError("requests required → pip install requests") from exc

        import requests as _req

        self._session = _req.Session()

        self._host = config.extra.get("host", "http://localhost:11434")

        self._url = f"{self._host}/api/embed"

        logger.info("Ollama session initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting Ollama embeddings for {len(texts)} text(s)")

            all_vectors: List[List[float]] = []

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing Ollama batch size: {len(batch)}")

                payload = {"model": self.config.model, "input": batch}

                response = self._session.post(self._url, json=payload)

                response.raise_for_status()

                data = response.json()

                all_vectors.extend(data["embeddings"])

            logger.info("Ollama embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("Ollama embedding generation failed")

            raise
