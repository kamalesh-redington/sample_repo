from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import Dict, List

from embedding.base import BaseEmbedder, EmbeddingConfig


class BM25Embedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing BM25Embedder")

        logger.debug(f"BM25 model configured: {config.model}")

        try:

            from rank_bm25 import BM25Okapi

        except ImportError as exc:

            logger.exception("rank_bm25 import failed")

            raise ImportError("rank_bm25 required → pip install rank-bm25") from exc

        self._bm25_class = BM25Okapi

        logger.info("BM25 initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(f"Starting BM25 sparse embeddings for {len(texts)} text(s)")

            tokenized = [text.split() for text in texts]

            logger.debug(f"Tokenized document count: {len(tokenized)}")

            bm25 = self._bm25_class(tokenized)

            embeddings = []

            for doc in tokenized:

                scores = bm25.get_scores(doc)

                embeddings.append(scores.tolist())

            logger.info("BM25 embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(embeddings)}")

            return embeddings

        except Exception as e:

            logger.exception("BM25 embedding generation failed")

            raise
