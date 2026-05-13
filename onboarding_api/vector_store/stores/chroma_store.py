"""
ChromaDB Local Vector Store
Type key : "chroma"
Backend  : ChromaDB (in-memory, on-disk, or HTTP server)

Extra config fields:
    mode       : "persistent" | "memory" | "http"  (default: persistent)
    persist_dir: "./chroma_data"
    host       : "localhost"    (http mode)
    port       : 8000           (http mode)
    tenant     : "default_tenant"
    database   : "default_database"
"""

from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig

_METRIC_MAP = {
    "cosine":      "cosine",
    "l2":          "l2",
    "dot_product": "ip",
}


class ChromaStore(BaseVectorStore):
    """ChromaDB vector store adapter."""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._client     = None
        self._collection = None

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError("chromadb required → pip install chromadb") from exc

        import chromadb

        mode = self.config.extra.get("mode", "persistent")

        if mode == "memory":
            self._client = chromadb.EphemeralClient()
        elif mode == "http":
            self._client = chromadb.HttpClient(
                host=self.config.host,
                port=self.config.extra.get("port", 8000),
            )
        else:   # persistent (default)
            persist_dir = self.config.extra.get("persist_dir", "./chroma_data")
            self._client = chromadb.PersistentClient(path=persist_dir)

        metric = _METRIC_MAP.get(self.config.index.metric, "cosine")
        self._collection = self._client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": metric},
        )

    def close(self) -> None:
        self._client     = None
        self._collection = None

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        for i in range(0, len(documents), self.config.insert_batch_size):
            batch = documents[i : i + self.config.insert_batch_size]
            self._collection.upsert(
                ids=[d.id for d in batch],
                embeddings=[d.vector for d in batch],
                documents=[d.text for d in batch],
                metadatas=[d.metadata or {} for d in batch],
            )

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        k = top_k or self.config.query_top_k
        kwargs: Dict[str, Any] = {
            "query_embeddings": [vector],
            "n_results":        k,
            "include":          ["documents", "metadatas", "distances"],
        }
        if filters:
            kwargs["where"] = {f"$and": [{k: {"$eq": v}} for k, v in filters.items()]}

        resp = self._collection.query(**kwargs)

        results = []
        for doc_id, text, meta, dist in zip(
            resp["ids"][0],
            resp["documents"][0],
            resp["metadatas"][0],
            resp["distances"][0],
        ):
            results.append(QueryResult(
                id=doc_id,
                score=1.0 - float(dist),   # convert distance to similarity score
                text=text,
                metadata=meta or {},
            ))
        return results

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        self._collection.delete(ids=ids)
