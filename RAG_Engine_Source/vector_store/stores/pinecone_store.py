"""
Pinecone Vector Store
Type key : "pinecone"
Backend  : Pinecone managed vector database

Supports:
    - Dense vectors (standard)
    - Hybrid (dense + sparse) via pinecone-client sparse_values

Extra config fields:
    api_key      : Pinecone API key (or env PINECONE_API_KEY)
    environment  : "us-east-1-aws"    (legacy; ignored in serverless)
    cloud        : "aws"              (serverless)
    region       : "us-east-1"       (serverless)
    namespace    : ""                 (partition within index)
    pod_type     : "p1.x1"           (pod-based; ignored in serverless)
    serverless   : true               (use Pinecone Serverless)
"""

import os
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig

_METRIC_MAP = {
    "cosine":      "cosine",
    "l2":          "euclidean",
    "dot_product": "dotproduct",
}


class PineconeStore(BaseVectorStore):
    """Pinecone managed vector database adapter."""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._index = None
        self._namespace = config.extra.get("namespace", "")

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            from pinecone import Pinecone, ServerlessSpec, PodSpec
        except ImportError as exc:
            raise ImportError("pinecone-client required → pip install pinecone-client") from exc

        from pinecone import Pinecone, ServerlessSpec, PodSpec

        api_key = self.config.extra.get("api_key") or os.environ.get("PINECONE_API_KEY", "")
        pc = Pinecone(api_key=api_key)

        index_name = self.config.collection_name
        metric     = _METRIC_MAP.get(self.config.index.metric, "cosine")
        dim        = self.config.extra.get("dimensions", 1536)

        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            if self.config.extra.get("serverless", True):
                spec = ServerlessSpec(
                    cloud=self.config.extra.get("cloud", "aws"),
                    region=self.config.extra.get("region", "us-east-1"),
                )
            else:
                spec = PodSpec(
                    environment=self.config.extra.get("environment", "us-east-1-aws"),
                    pod_type=self.config.extra.get("pod_type", "p1.x1"),
                )
            pc.create_index(name=index_name, dimension=dim, metric=metric, spec=spec)

        self._index = pc.Index(index_name)

    def close(self) -> None:
        self._index = None

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        for i in range(0, len(documents), self.config.insert_batch_size):
            batch = documents[i : i + self.config.insert_batch_size]
            vectors = []
            for doc in batch:
                record: Dict[str, Any] = {
                    "id":     doc.id,
                    "values": doc.vector,
                    "metadata": {**doc.metadata, "_text": doc.text},
                }
                if doc.sparse:
                    record["sparse_values"] = {
                        "indices": list(doc.sparse.keys()),
                        "values":  list(doc.sparse.values()),
                    }
                vectors.append(record)
            self._index.upsert(vectors=vectors, namespace=self._namespace)

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        k = top_k or self.config.query_top_k
        kwargs: Dict[str, Any] = {
            "vector":          vector,
            "top_k":           k,
            "include_metadata": True,
            "namespace":       self._namespace,
        }
        if filters:
            kwargs["filter"] = filters

        response = self._index.query(**kwargs)
        results = []
        for match in response.matches:
            meta = dict(match.metadata or {})
            text = meta.pop("_text", "")
            results.append(QueryResult(
                id=match.id,
                score=float(match.score),
                text=text,
                metadata=meta,
            ))
        return results

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        self._index.delete(ids=ids, namespace=self._namespace)
