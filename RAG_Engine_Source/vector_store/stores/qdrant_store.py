"""
Qdrant Vector Store
Type key : "qdrant"
Backend  : Qdrant (local via Docker or Qdrant Cloud)

Supports:
    - Dense search
    - Payload (metadata) filtering
    - Named vectors (multi-vector per point)

Extra config fields:
    url       : "http://localhost:6333"
    api_key   : Qdrant Cloud API key (or env QDRANT_API_KEY)
    https     : false
    on_disk   : false   (store vectors on disk for large datasets)
"""

import os
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig

_METRIC_MAP = {
    "cosine":      "Cosine",
    "l2":          "Euclid",
    "dot_product": "Dot",
}


class QdrantStore(BaseVectorStore):
    """Qdrant vector database adapter."""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._client = None

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise ImportError("qdrant-client required → pip install qdrant-client") from exc

        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        api_key = self.config.extra.get("api_key") or os.environ.get("QDRANT_API_KEY")
        url     = self.config.extra.get("url", f"http://{self.config.host}:{self.config.port}")

        self._client = QdrantClient(url=url, api_key=api_key)

        distance = Distance[_METRIC_MAP.get(self.config.index.metric, "Cosine").upper()]
        dim      = self.config.extra.get("dimensions", 1536)

        existing = [c.name for c in self._client.get_collections().collections]
        if self.config.collection_name not in existing:
            self._client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(size=dim, distance=distance,
                                            on_disk=self.config.extra.get("on_disk", False)),
            )

    def close(self) -> None:
        self._client = None

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        from qdrant_client.models import PointStruct

        for i in range(0, len(documents), self.config.insert_batch_size):
            batch = documents[i : i + self.config.insert_batch_size]
            points = [
                PointStruct(
                    id=self._to_uint64(doc.id),
                    vector=doc.vector,
                    payload={**doc.metadata, "_text": doc.text, "_id": doc.id},
                )
                for doc in batch
            ]
            self._client.upsert(
                collection_name=self.config.collection_name,
                points=points,
            )

    @staticmethod
    def _to_uint64(doc_id: str) -> int:
        """Qdrant requires integer point IDs — hash the string id."""
        import hashlib
        return int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % (2**63)

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        k = top_k or self.config.query_top_k
        qdrant_filter = None

        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        hits = self._client.search(
            collection_name=self.config.collection_name,
            query_vector=vector,
            limit=k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        results = []
        for hit in hits:
            payload = dict(hit.payload or {})
            text    = payload.pop("_text", "")
            doc_id  = payload.pop("_id", str(hit.id))
            results.append(QueryResult(
                id=doc_id,
                score=float(hit.score),
                text=text,
                metadata=payload,
            ))
        return results

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        from qdrant_client.models import PointIdsList
        int_ids = [self._to_uint64(i) for i in ids]
        self._client.delete(
            collection_name=self.config.collection_name,
            points_selector=PointIdsList(points=int_ids),
        )
