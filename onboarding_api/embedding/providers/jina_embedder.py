from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class JinaEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing JinaEmbedder")

        logger.debug(f"Jina model configured: {config.model}")

        try:

            import requests

        except ImportError as exc:

            logger.exception("requests import failed")

            raise ImportError("requests required → pip install requests") from exc

        import requests as _req

        self._session = _req.Session()

        self._api_key = config.extra.get("api_key")

        self._url = "https://api.jina.ai/v1/embeddings"

        logger.info("Jina API client initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting Jina embeddings for {len(texts)} text(s)")

            all_vectors: List[List[float]] = []

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing Jina batch size: {len(batch)}")

                payload = {"model": self.config.model, "input": batch}

                response = self._session.post(
                    self._url,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()

                result = response.json()

                for item in result["data"]:

                    all_vectors.append(item["embedding"])

            logger.info("Jina embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("Jina embedding generation failed")

            raise
