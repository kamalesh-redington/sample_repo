"""
Base interfaces for the vector_store abstraction layer.

Every concrete store MUST implement BaseVectorStore.
The VectorStoreConfig dataclass is the single parsing point for
config.yaml → vector_store + object_store sections.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class VectorDocument:
    """
    A single chunk ready for upsert.

    Attributes:
        id        : unique string identifier (e.g. UUID or doc+chunk index)
        vector    : dense float embedding
        text      : original chunk text (stored alongside the vector)
        metadata  : arbitrary key/value metadata (source, page, etc.)
        sparse    : optional sparse dict {token_id: weight} for hybrid stores
    """
    id: str
    vector: List[float]
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sparse: Optional[Dict[int, float]] = None   # for Pinecone hybrid / Weaviate BM25


@dataclass
class QueryResult:
    """A single result returned from a similarity search."""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Config dataclasses ────────────────────────────────────────────────────────

@dataclass
class IndexConfig:
    type: str = "hnsw"             # flat | ivfflat | hnsw | diskann
    metric: str = "cosine"         # cosine | l2 | dot_product
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "IndexConfig":
        return cls(
            type=d.get("type", "hnsw"),
            metric=d.get("metric", "cosine"),
            params=d.get("params", {}),
        )


@dataclass
class VectorStoreConfig:
    """
    Parsed from config.yaml → vector_store section.

    Flattened representation that every store adapter reads from.
    Provider-specific extras are stored in `extra`.
    """

    type: str                          # pgvector | pinecone | weaviate | milvus |
                                       # qdrant | elasticsearch | opensearch |
                                       # faiss | chroma | s3_vector |
                                       # gcs_vector | azure_blob_vector

    # ── connection block ──
    host: str = "localhost"
    port: int = 5432
    database: str = "ragdb"
    user: str = "postgres"
    password: str = ""

    # ── collection / table ──
    collection_name: str = "document_chunks"
    schema: str = "public"

    # ── index ──
    index: IndexConfig = field(default_factory=IndexConfig)

    # ── batching ──
    insert_batch_size: int = 100
    query_top_k: int = 10

    # ── hybrid storage strategy ──
    storage_strategy: str = "db_only"   # db_only | s3_only | hybrid

    # ── provider-specific overflows ──
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "VectorStoreConfig":
        vs = config.get("vector_store", {})

        conn = vs.get("connection", {})
        col  = vs.get("collection", {})
        bat  = vs.get("batching", {})

        # Support both flat (legacy) and nested (new) YAML layouts
        known = {
            "type", "connection", "collection", "index",
            "batching", "storage_strategy",
        }
        extra = {k: v for k, v in vs.items() if k not in known}
        # Also absorb legacy flat keys
        for legacy in ("host", "port", "database", "user", "password",
                       "table", "index_type"):
            if legacy in vs:
                extra[legacy] = vs[legacy]

        return cls(
            type=vs.get("type", "faiss"),
            host=conn.get("host", vs.get("host", "localhost")),
            port=int(conn.get("port", vs.get("port", 5432))),
            database=conn.get("database", vs.get("database", "ragdb")),
            user=conn.get("user", vs.get("user", "postgres")),
            password=conn.get("password", vs.get("password", "")),
            collection_name=col.get("name", vs.get("table", "document_chunks")),
            schema=col.get("schema", "public"),
            index=IndexConfig.from_dict(vs.get("index", {})),
            insert_batch_size=bat.get("insert_batch_size", vs.get("insert_batch_size", 100)),
            query_top_k=bat.get("query_top_k", vs.get("query_top_k", 10)),
            storage_strategy=vs.get("storage_strategy", "db_only"),
            extra=extra,
        )


@dataclass
class ObjectStoreConfig:
    """
    Parsed from config.yaml → object_store section.
    Used by S3VectorStore, GCSVectorStore, AzureBlobVectorStore
    and the hybrid storage strategy.
    """

    provider: str = "s3"
    bucket: str = ""
    region: str = "us-east-1"
    prefix: str = "embeddings/"
    access_key: str = ""
    secret_key: str = ""
    storage_format: str = "parquet"    # parquet | npy | json
    embeddings_path: str = "embeddings/"
    documents_path: str = "documents/"
    metadata_path: str = "metadata/"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "ObjectStoreConfig":
        os_cfg = config.get("object_store", {})
        creds  = os_cfg.get("credentials", {})
        layout = os_cfg.get("layout", {})
        known  = {"provider", "bucket", "region", "prefix",
                  "credentials", "storage_format", "layout"}
        extra  = {k: v for k, v in os_cfg.items() if k not in known}
        return cls(
            provider=os_cfg.get("provider", "s3"),
            bucket=os_cfg.get("bucket", ""),
            region=os_cfg.get("region", "us-east-1"),
            prefix=os_cfg.get("prefix", "embeddings/"),
            access_key=creds.get("access_key", ""),
            secret_key=creds.get("secret_key", ""),
            storage_format=os_cfg.get("storage_format", "parquet"),
            embeddings_path=layout.get("embeddings_path", "embeddings/"),
            documents_path=layout.get("documents_path", "documents/"),
            metadata_path=layout.get("metadata_path", "metadata/"),
            extra=extra,
        )


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseVectorStore(ABC):
    """
    Abstract interface every vector store adapter must satisfy.

    Lifecycle:
        store = SomeVectorStore(vs_config)
        store.connect()                            # establish connection
        store.upsert(docs)                         # insert / update
        results = store.query(vec, top_k=5)        # similarity search
        store.delete(ids)                          # remove by id
        store.close()                              # clean up
    """

    def __init__(self, config: VectorStoreConfig):
        self.config = config

    # ── connection ────────────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> None:
        """Open connection / validate credentials."""

    @abstractmethod
    def close(self) -> None:
        """Close connection and release resources."""

    # ── write ─────────────────────────────────────────────────────────────────

    @abstractmethod
    def upsert(self, documents: List[VectorDocument]) -> None:
        """
        Insert or update a list of VectorDocuments.
        Batching is handled internally using config.insert_batch_size.
        """

    # ── read ──────────────────────────────────────────────────────────────────

    @abstractmethod
    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        """
        Run a similarity search.

        Args:
            vector  : Query embedding.
            top_k   : Number of results (defaults to config.query_top_k).
            filters : Metadata filters (provider-specific format is normalised
                      inside each adapter).

        Returns:
            Ordered list of QueryResult (best match first).
        """

    # ── delete ────────────────────────────────────────────────────────────────

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete documents by their ids."""

    # ── helpers ───────────────────────────────────────────────────────────────

    def info(self) -> Dict[str, Any]:
        """Return store metadata (useful for logging)."""
        return {
            "type": self.config.type,
            "collection": self.config.collection_name,
            "index_type": self.config.index.type,
            "metric": self.config.index.metric,
            "strategy": self.config.storage_strategy,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"type={self.config.type!r}, "
            f"collection={self.config.collection_name!r})"
        )

    # ── context manager ───────────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()
