from config.logger import setup_logger

logger = setup_logger(__name__)

import os
from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore,
    QueryResult,
    VectorDocument,
    VectorStoreConfig,
)

_METRIC_MAP = {
    "cosine": "cosine",
    "l2": "euclidean",
    "dot_product": "dotproduct",
}


class PineconeStore(BaseVectorStore):

    def __init__(self, config: VectorStoreConfig):

        super().__init__(config)

        logger.info("Initializing PineconeStore")

        self._index = None

        self._namespace = config.extra.get("namespace", "")

        logger.debug(f"Pinecone namespace: {self._namespace}")

    # ─────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────

    def connect(self) -> None:

        try:

            logger.info("Connecting to Pinecone")

            from pinecone import Pinecone, ServerlessSpec, PodSpec

        except ImportError as exc:

            logger.exception("pinecone-client import failed")

            raise ImportError(
                "pinecone-client required → pip install pinecone-client"
            ) from exc

        from pinecone import Pinecone, ServerlessSpec, PodSpec

        api_key = self.config.extra.get("api_key") or os.environ.get(
            "PINECONE_API_KEY", ""
        )

        pc = Pinecone(api_key=api_key)

        index_name = self.config.collection_name

        metric = _METRIC_MAP.get(self.config.index.metric, "cosine")

        dim = self.config.extra.get("dimensions", 1536)

        logger.debug(f"Pinecone index name: {index_name}")

        logger.debug(f"Pinecone dimensions: {dim}")

        logger.debug(f"Pinecone metric: {metric}")

        existing = [idx.name for idx in pc.list_indexes()]

        if index_name not in existing:

            logger.info("Pinecone index does not exist, creating new index")

            if self.config.extra.get("serverless", True):

                spec = ServerlessSpec(
                    cloud=self.config.extra.get("cloud", "aws"),
                    region=self.config.extra.get("region", "us-east-1"),
                )

                logger.info("Using Pinecone serverless configuration")

            else:

                spec = PodSpec(
                    environment=self.config.extra.get("environment", "us-east-1-aws"),
                    pod_type=self.config.extra.get("pod_type", "p1.x1"),
                )

                logger.info("Using Pinecone pod configuration")

            pc.create_index(name=index_name, dimension=dim, metric=metric, spec=spec)

            logger.info("Pinecone index created successfully")

        self._index = pc.Index(index_name)

        logger.info("Connected to Pinecone successfully")

    def close(self) -> None:

        logger.info("Closing Pinecone connection")

        self._index = None

    # ─────────────────────────────────────────────
    # Write
    # ─────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:

        try:

            logger.info(f"Starting Pinecone upsert for {len(documents)} documents")

            for i in range(0, len(documents), self.config.insert_batch_size):

                batch = documents[i : i + self.config.insert_batch_size]

                logger.debug(f"Processing Pinecone batch size: {len(batch)}")

                vectors = []

                for doc in batch:

                    record: Dict[str, Any] = {
                        "id": doc.id,
                        "values": doc.vector,
                        "metadata": {
                            **doc.metadata,
                            "_text": doc.text,
                        },
                    }

                    if doc.sparse:

                        logger.debug(f"Sparse vector detected for document: {doc.id}")

                        record["sparse_values"] = {
                            "indices": list(doc.sparse.keys()),
                            "values": list(doc.sparse.values()),
                        }

                    vectors.append(record)

                self._index.upsert(vectors=vectors, namespace=self._namespace)

            logger.info("Pinecone upsert completed successfully")

        except Exception as e:

            logger.exception("Pinecone upsert failed")

            raise

    # ─────────────────────────────────────────────
    # Read
    # ─────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:

        try:

            logger.info("Starting Pinecone vector query")

            k = top_k or self.config.query_top_k

            logger.debug(f"Pinecone top_k: {k}")

            kwargs: Dict[str, Any] = {
                "vector": vector,
                "top_k": k,
                "include_metadata": True,
                "namespace": self._namespace,
            }

            if filters:

                logger.debug(f"Pinecone filters applied: {filters}")

                kwargs["filter"] = filters

            response = self._index.query(**kwargs)

            results = []

            for match in response.matches:

                meta = dict(match.metadata or {})

                text = meta.pop("_text", "")

                results.append(
                    QueryResult(
                        id=match.id,
                        score=float(match.score),
                        text=text,
                        metadata=meta,
                    )
                )

            logger.info(f"Pinecone query returned {len(results)} results")

            return results

        except Exception as e:

            logger.exception("Pinecone query failed")

            raise

    # ─────────────────────────────────────────────
    # Delete
    # ─────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:

        try:

            logger.info(f"Deleting {len(ids)} vectors from Pinecone")

            self._index.delete(ids=ids, namespace=self._namespace)

            logger.info("Pinecone delete completed successfully")

        except Exception as e:

            logger.exception("Pinecone delete failed")

            raise
