from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore,
    QueryResult,
    VectorDocument,
    VectorStoreConfig,
)


class ElasticsearchStore(BaseVectorStore):

    def __init__(self, config: VectorStoreConfig):

        super().__init__(config)

        logger.info("Initializing ElasticsearchStore")

        self._client = None

    def connect(self) -> None:

        try:

            logger.info("Connecting to Elasticsearch")

            from elasticsearch import Elasticsearch

        except ImportError as exc:

            logger.exception("elasticsearch import failed")

            raise ImportError(
                "elasticsearch required → pip install elasticsearch"
            ) from exc

        from elasticsearch import Elasticsearch

        self._client = Elasticsearch(self.config.extra.get("hosts"))

        logger.info("Connected to Elasticsearch successfully")

    def close(self) -> None:

        logger.info("Closing Elasticsearch connection")

        self._client = None

    def upsert(self, documents: List[VectorDocument]) -> None:

        try:

            logger.info(f"Starting Elasticsearch upsert for {len(documents)} documents")

            logger.warning("Elasticsearch upsert implementation pending")

        except Exception as e:

            logger.exception("Elasticsearch upsert failed")

            raise

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:

        try:

            logger.info("Starting Elasticsearch query")

            logger.warning("Elasticsearch query implementation pending")

            return []

        except Exception as e:

            logger.exception("Elasticsearch query failed")

            raise

    def delete(self, ids: List[str]) -> None:

        logger.info(f"Deleting {len(ids)} vectors from Elasticsearch")

        logger.warning("Elasticsearch delete implementation pending")
