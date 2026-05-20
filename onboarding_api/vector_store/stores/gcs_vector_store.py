from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore,
    QueryResult,
    VectorDocument,
    VectorStoreConfig,
)


class GCSVectorStore(BaseVectorStore):

    def __init__(self, config: VectorStoreConfig):

        super().__init__(config)

        logger.info("Initializing GCSVectorStore")

        self._client = None
        self._bucket = None

    # ─────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────

    def connect(self) -> None:

        try:

            logger.info("Connecting to Google Cloud Storage")

            from google.cloud import storage

        except ImportError as exc:

            logger.exception("google-cloud-storage import failed")

            raise ImportError(
                "google-cloud-storage required → pip install google-cloud-storage"
            ) from exc

        from google.cloud import storage

        self._client = storage.Client()

        bucket_name = self.config.extra.get("bucket_name")

        logger.debug(f"GCS bucket name: {bucket_name}")

        self._bucket = self._client.bucket(bucket_name)

        logger.info("Connected to Google Cloud Storage successfully")

    # ─────────────────────────────────────────────
    # Close
    # ─────────────────────────────────────────────

    def close(self) -> None:

        logger.info("Closing Google Cloud Storage connection")

        self._client = None
        self._bucket = None

    # ─────────────────────────────────────────────
    # Upsert
    # ─────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:

        try:

            logger.info(
                f"Starting GCS vector persistence for {len(documents)} documents"
            )

            logger.warning("GCS vector persistence implementation pending")

        except Exception as e:

            logger.exception("GCS vector persistence failed")

            raise

    # ─────────────────────────────────────────────
    # Query
    # ─────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:

        try:

            logger.info("Starting GCS vector query")

            logger.warning("GCS vector query implementation pending")

            return []

        except Exception as e:

            logger.exception("GCS vector query failed")

            raise

    # ─────────────────────────────────────────────
    # Delete
    # ─────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:

        try:

            logger.info(f"Deleting {len(ids)} vectors from GCS store")

            logger.warning("GCS vector delete implementation pending")

        except Exception as e:

            logger.exception("GCS vector delete failed")

            raise
