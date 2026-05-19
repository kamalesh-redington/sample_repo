"""
Weaviate Vector Store
Type key : "weaviate"
Backend  : Weaviate vector database (local or cloud)

Supports:
    - Dense search (nearVector)
    - Hybrid search (hybrid query = dense + BM25)
    - Metadata filtering (where filter)

Extra config fields:
    url           : "http://localhost:8080"
    api_key       : WCS API key (or env WEAVIATE_API_KEY)
    class_name    : maps to collection_name
    text_key      : "text"   (property storing the chunk text)
    hybrid_alpha  : 0.75     (dense weight in hybrid, 0=sparse, 1=dense)
"""

import os
import uuid
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig


class WeaviateStore(BaseVectorStore):
    """Weaviate vector database adapter (weaviate-client v4)."""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._client = None
        self._class  = config.extra.get("class_name", config.collection_name)
        self._text_key = config.extra.get("text_key", "text")

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            import weaviate
            from weaviate.auth import AuthApiKey
        except ImportError as exc:
            raise ImportError("weaviate-client required → pip install weaviate-client") from exc

        import weaviate
        from weaviate.auth import AuthApiKey

        url     = self.config.extra.get("url", f"http://{self.config.host}:{self.config.port}")
        api_key = self.config.extra.get("api_key") or os.environ.get("WEAVIATE_API_KEY")

        auth = AuthApiKey(api_key=api_key) if api_key else None
        self._client = weaviate.connect_to_custom(
            http_host=self.config.host,
            http_port=self.config.port,
            http_secure=self.config.extra.get("secure", False),
            grpc_host=self.config.extra.get("grpc_host", self.config.host),
            grpc_port=self.config.extra.get("grpc_port", 50051),
            grpc_secure=self.config.extra.get("grpc_secure", False),
            auth_credentials=auth,
        )
        self._ensure_collection()

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # ── schema helpers ────────────────────────────────────────────────────────

    def _ensure_collection(self) -> None:
        from weaviate.classes.config import Configure, Property, DataType

        if not self._client.collections.exists(self._class):
            metric = self.config.index.metric
            dist   = {"cosine": "cosine", "l2": "l2-squared", "dot_product": "dot"}.get(metric, "cosine")
            self._client.collections.create(
                name=self._class,
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=dist,
                    ef_construction=self.config.index.params.get("ef_construction", 128),
                    max_connections=self.config.index.params.get("m", 64),
                ),
                properties=[
                    Property(name=self._text_key, data_type=DataType.TEXT),
                    Property(name="doc_id",        data_type=DataType.TEXT),
                ],
            )

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        col = self._client.collections.get(self._class)
        for i in range(0, len(documents), self.config.insert_batch_size):
            batch = documents[i : i + self.config.insert_batch_size]
            with col.batch.dynamic() as wb:
                for doc in batch:
                    props = {self._text_key: doc.text, **doc.metadata}
                    wb.add_object(
                        properties=props,
                        vector=doc.vector,
                        uuid=str(uuid.UUID(doc.id)) if self._is_valid_uuid(doc.id) else None,
                    )

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        try:
            uuid.UUID(val)
            return True
        except ValueError:
            return False

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        from weaviate.classes.query import MetadataQuery

        k    = top_k or self.config.query_top_k
        col  = self._client.collections.get(self._class)
        alpha = self.config.extra.get("hybrid_alpha", 1.0)  # 1.0 = fully dense

        response = col.query.hybrid(
            query=None,
            vector=vector,
            alpha=alpha,
            limit=k,
            return_metadata=MetadataQuery(score=True),
        )

        return [
            QueryResult(
                id=str(obj.uuid),
                score=obj.metadata.score or 0.0,
                text=obj.properties.get(self._text_key, ""),
                metadata={k: v for k, v in obj.properties.items() if k != self._text_key},
            )
            for obj in response.objects
        ]

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        col = self._client.collections.get(self._class)
        for doc_id in ids:
            col.data.delete_by_id(doc_id)
