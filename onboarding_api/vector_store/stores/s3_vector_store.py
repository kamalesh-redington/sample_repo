from config.logger import setup_logger

logger = setup_logger(__name__)

import os
from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore,
    ObjectStoreConfig,
    QueryResult,
    VectorDocument,
    VectorStoreConfig,
)


class S3VectorStore(BaseVectorStore):
    """
    AWS Managed S3 Vector Store
    """

    def __init__(
        self,
        config: VectorStoreConfig,
        object_config: Optional[ObjectStoreConfig] = None,
    ):
        super().__init__(config)

        logger.info("Initializing S3VectorStore")

        self._obj_cfg = object_config or ObjectStoreConfig()

        self._s3 = None
        self._bucket = None
        self._index_name = None

    # ──────────────────────────────────────────────────────────
    # Connection
    # ──────────────────────────────────────────────────────────

    def connect(self) -> None:

        try:

            logger.info("Connecting to S3 Vector Store")

            import boto3

            region = self._obj_cfg.region or os.environ.get("AWS_DEFAULT_REGION")

            self._s3 = boto3.client(
                "s3vectors",
                region_name=region,
                aws_access_key_id=(
                    self._obj_cfg.access_key or os.environ.get("AWS_ACCESS_KEY_ID")
                ),
                aws_secret_access_key=(
                    self._obj_cfg.secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
                ),
            )

            self._bucket = self._obj_cfg.bucket or self.config.collection_name

            self._index_name = self.config.extra.get(
                "index_name",
                "rag-index",
            )

            logger.info("Connected to S3 Vector Store successfully")

            logger.debug(f"S3 bucket: {self._bucket}")

            logger.debug(f"S3 index name: {self._index_name}")

            logger.debug(f"AWS region: {region}")

        except Exception as exc:

            logger.exception(f"S3 Vector Store connection failed: {exc}")

            raise

    def close(self) -> None:
        """
        Managed service handles persistence automatically
        """

        logger.info("Closing S3 Vector Store connection")

    # ──────────────────────────────────────────────────────────
    # Write
    # ──────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        """
        Insert or update vectors
        """

        if not documents:

            logger.warning("No documents received for S3 vector upload")

            return

        logger.info(f"Starting S3 vector upsert for {len(documents)} documents")

        vectors_payload = []

        for doc in documents:

            logger.debug(f"Preparing vector payload for document: {doc.id}")

            vectors_payload.append(
                {
                    "key": doc.id,
                    "data": {
                        "float32": doc.vector,
                    },
                    "metadata": {
                        **(doc.metadata or {}),
                        "text": doc.text,
                    },
                }
            )

        try:

            response = self._s3.put_vectors(
                vectorBucketName=self._bucket,
                indexName=self._index_name,
                vectors=vectors_payload,
            )

            logger.info(f"S3 vector upload completed for {len(documents)} documents")

            logger.debug(f"S3 upload response: {response}")

        except Exception as exc:

            logger.exception(f"S3 vector upload failed: {exc}")

            raise

    # ──────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        """
        Query similar vectors
        """

        k = top_k or self.config.query_top_k

        logger.info("Starting S3 vector query")

        logger.debug(f"S3 top_k: {k}")

        try:

            response = self._s3.query_vectors(
                vectorBucketName=self._bucket,
                indexName=self._index_name,
                queryVector=vector,
                topK=k,
            )

        except Exception as exc:

            logger.exception(f"S3 vector query failed: {exc}")

            raise

        results = []

        for match in response.get("matches", []):

            metadata = match.get("metadata", {})

            # Optional local metadata filtering
            if filters:

                passed = all(
                    metadata.get(key) == value for key, value in filters.items()
                )

                if not passed:

                    logger.debug(f"Filtered out vector result: {match.get('key')}")

                    continue

            logger.debug(f"Matched vector ID: {match.get('key')}")

            results.append(
                QueryResult(
                    id=match.get("key"),
                    score=float(match.get("score", 0.0)),
                    text=metadata.get("text", ""),
                    metadata=metadata,
                )
            )

        logger.info(f"S3 vector query returned {len(results)} results")

        return results

    # ──────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        """
        Delete vectors by IDs
        """

        if not ids:
            return

        logger.info(f"Deleting {len(ids)} vectors from S3 Vector Store")

        try:

            self._s3.delete_vectors(
                vectorBucketName=self._bucket,
                indexName=self._index_name,
                keys=ids,
            )

            logger.info(f"S3 vector delete completed for {len(ids)} vectors")

        except Exception as exc:

            logger.exception(f"S3 vector delete failed: {exc}")

            raise
