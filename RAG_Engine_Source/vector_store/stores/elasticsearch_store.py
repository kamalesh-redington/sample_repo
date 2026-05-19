"""
Elasticsearch / OpenSearch Vector Store
Type key  : "elasticsearch"  |  "opensearch"
Backend   : Elasticsearch 8.x (knn_dense_vector) OR OpenSearch 2.x (knn plugin)

Extra config fields:
    url       : "http://localhost:9200"
    api_key   : ES Cloud API key  (or env ELASTICSEARCH_API_KEY)
    username  : "elastic"
    password  : (or env ELASTICSEARCH_PASSWORD)
    num_shards   : 1
    num_replicas : 0
"""

import os
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig


class ElasticsearchStore(BaseVectorStore):
    """
    Elasticsearch 8.x dense_vector kNN store.
    Set type: "opensearch" in config to use the OpenSearch client instead.
    """

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._es     = None
        self._is_os  = config.type == "opensearch"  # flag for client selection

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        url      = self.config.extra.get("url", f"http://{self.config.host}:{self.config.port}")
        api_key  = self.config.extra.get("api_key") or os.environ.get("ELASTICSEARCH_API_KEY")
        username = self.config.extra.get("username", self.config.user or "elastic")
        password = self.config.extra.get("password", self.config.password) or os.environ.get("ELASTICSEARCH_PASSWORD", "")

        if self._is_os:
            try:
                from opensearchpy import OpenSearch, RequestsHttpConnection
            except ImportError as exc:
                raise ImportError("opensearch-py required → pip install opensearch-py") from exc
            from opensearchpy import OpenSearch
            self._es = OpenSearch(
                hosts=[url],
                http_auth=(username, password) if password else None,
                use_ssl="https" in url,
                verify_certs=False,
            )
        else:
            try:
                from elasticsearch import Elasticsearch
            except ImportError as exc:
                raise ImportError("elasticsearch required → pip install elasticsearch") from exc
            from elasticsearch import Elasticsearch
            auth = {"api_key": api_key} if api_key else {"basic_auth": (username, password)}
            self._es = Elasticsearch(url, **auth)

        self._ensure_index()

    def close(self) -> None:
        if self._es:
            self._es.close()
            self._es = None

    # ── schema helpers ────────────────────────────────────────────────────────

    def _ensure_index(self) -> None:
        dim    = self.config.extra.get("dimensions", 1536)
        metric = {"cosine": "cosine", "l2": "l2_norm", "dot_product": "dot_product"}.get(
            self.config.index.metric, "cosine"
        )
        if not self._es.indices.exists(index=self.config.collection_name):
            mapping = {
                "settings": {
                    "number_of_shards":   self.config.extra.get("num_shards", 1),
                    "number_of_replicas": self.config.extra.get("num_replicas", 0),
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type":         "dense_vector",
                            "dims":         dim,
                            "index":        True,
                            "similarity":   metric,
                        },
                        "text":     {"type": "text"},
                        "metadata": {"type": "object", "dynamic": True},
                    }
                },
            }
            self._es.indices.create(index=self.config.collection_name, body=mapping)

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        from elasticsearch.helpers import bulk

        def _gen():
            for doc in documents:
                yield {
                    "_index": self.config.collection_name,
                    "_id":    doc.id,
                    "_source": {
                        "embedding": doc.vector,
                        "text":      doc.text,
                        "metadata":  doc.metadata,
                    },
                }

        bulk(self._es, _gen(), chunk_size=self.config.insert_batch_size)

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        k = top_k or self.config.query_top_k
        knn: Dict[str, Any] = {
            "field":          "embedding",
            "query_vector":   vector,
            "num_candidates": k * 2,
            "k":              k,
        }
        body: Dict[str, Any] = {"knn": knn, "_source": ["text", "metadata"]}

        if filters:
            body["query"] = {
                "bool": {
                    "filter": [{"term": {f"metadata.{fk}": fv}} for fk, fv in filters.items()]
                }
            }

        resp = self._es.search(index=self.config.collection_name, body=body)
        return [
            QueryResult(
                id=hit["_id"],
                score=float(hit["_score"]),
                text=hit["_source"].get("text", ""),
                metadata=hit["_source"].get("metadata", {}),
            )
            for hit in resp["hits"]["hits"]
        ]

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        from elasticsearch.helpers import bulk
        actions = [{"_op_type": "delete", "_index": self.config.collection_name, "_id": i} for i in ids]
        bulk(self._es, actions)
