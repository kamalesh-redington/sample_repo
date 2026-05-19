"""
Milvus Vector Store
Type key : "milvus"
Backend  : Milvus (local via Docker or Zilliz Cloud)

Supports:
    - IVF_FLAT, IVF_SQ8, HNSW index types
    - Metadata scalar filtering

Extra config fields:
    uri       : "http://localhost:19530"  OR  "tcp://localhost:19530"
    token     : Zilliz Cloud token (or env MILVUS_TOKEN)
    dim       : 1536
"""

import os
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig

_METRIC_MAP = {
    "cosine":      "COSINE",
    "l2":          "L2",
    "dot_product": "IP",
}

_INDEX_TYPE_MAP = {
    "flat":    "FLAT",
    "ivf":     "IVF_FLAT",
    "ivfflat": "IVF_FLAT",
    "hnsw":    "HNSW",
    "diskann": "DISKANN",
}


class MilvusStore(BaseVectorStore):
    """Milvus vector database adapter (pymilvus)."""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._col = None

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            from pymilvus import (
                MilvusClient, DataType, FieldSchema, CollectionSchema, Collection,
                connections, utility
            )
        except ImportError as exc:
            raise ImportError("pymilvus required → pip install pymilvus") from exc

        from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType

        token = self.config.extra.get("token") or os.environ.get("MILVUS_TOKEN", "")
        uri   = self.config.extra.get("uri", f"http://{self.config.host}:{self.config.port}")
        dim   = self.config.extra.get("dimensions", 1536)

        connections.connect(alias="default", uri=uri, token=token)

        col_name = self.config.collection_name
        if not utility.has_collection(col_name):
            fields = [
                FieldSchema(name="id",        dtype=DataType.VARCHAR, is_primary=True, max_length=256),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
                FieldSchema(name="text",      dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata",  dtype=DataType.JSON),
            ]
            schema = CollectionSchema(fields=fields)
            self._col = Collection(name=col_name, schema=schema)

            idx_type = _INDEX_TYPE_MAP.get(self.config.index.type, "HNSW")
            metric   = _METRIC_MAP.get(self.config.index.metric, "COSINE")
            params   = self.config.index.params or {"M": 16, "efConstruction": 200}
            self._col.create_index(
                field_name="embedding",
                index_params={"metric_type": metric, "index_type": idx_type, "params": params},
            )
        else:
            self._col = Collection(name=col_name)

        self._col.load()

    def close(self) -> None:
        from pymilvus import connections
        connections.disconnect("default")
        self._col = None

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        import json as _json

        for i in range(0, len(documents), self.config.insert_batch_size):
            batch = documents[i : i + self.config.insert_batch_size]
            data = {
                "id":        [d.id for d in batch],
                "embedding": [d.vector for d in batch],
                "text":      [d.text for d in batch],
                "metadata":  [d.metadata for d in batch],
            }
            self._col.upsert(data)

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        k         = top_k or self.config.query_top_k
        metric    = _METRIC_MAP.get(self.config.index.metric, "COSINE")
        expr      = " && ".join([f'metadata["{k}"] == "{v}"' for k, v in (filters or {}).items()]) or None

        results_raw = self._col.search(
            data=[vector],
            anns_field="embedding",
            param={"metric_type": metric, "params": {"ef": 64}},
            limit=k,
            expr=expr,
            output_fields=["id", "text", "metadata"],
        )

        return [
            QueryResult(
                id=hit.entity.get("id"),
                score=float(hit.distance),
                text=hit.entity.get("text", ""),
                metadata=hit.entity.get("metadata", {}),
            )
            for hit in results_raw[0]
        ]

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        expr = f'id in {ids}'
        self._col.delete(expr)
