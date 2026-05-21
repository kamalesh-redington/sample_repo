"""
VectorStoreFactory — config-driven vector store instantiation.

Usage
-----
    from vector_store.factory import VectorStoreFactory

    store = VectorStoreFactory.create(config)
    store = VectorStoreFactory.create_from_yaml("config.yaml")

    with store:                             # calls connect() / close() automatically
        store.upsert(docs)
        results = store.query(vec, top_k=5)

    # Or manually:
    store.connect()
    store.upsert(docs)
    store.close()

Supported types
---------------
    Relational DB:       pgvector
    Managed vector DB:   pinecone | weaviate | milvus | qdrant
    Search engines:      elasticsearch | opensearch
    Local / embedded:    faiss | chroma
    Cloud object store:  s3_vector | gcs_vector | azure_blob_vector

Plugin hook
-----------
    VectorStoreFactory.register("my_store", "myapp.stores.MyStore")
"""

from config.logger import setup_logger

logger = setup_logger(__name__)
from config.timer import log_execution_time

from typing import Optional, Type

from vector_store.base import BaseVectorStore, ObjectStoreConfig, VectorStoreConfig

# ── provider registry ──────────────────────────────────────────────────────────
# Dotted class paths → lazily imported when the type is actually requested.

_REGISTRY: dict[str, str] = {
    # Relational + extension
    "pgvector": "vector_store.stores.pgvector_store.PGVectorStore",
    # Managed vector databases
    "pinecone": "vector_store.stores.pinecone_store.PineconeStore",
    "weaviate": "vector_store.stores.weaviate_store.WeaviateStore",
    "milvus": "vector_store.stores.milvus_store.MilvusStore",
    "qdrant": "vector_store.stores.qdrant_store.QdrantStore",
    # Search engines with vector support
    "elasticsearch": "vector_store.stores.elasticsearch_store.ElasticsearchStore",
    "opensearch": "vector_store.stores.elasticsearch_store.ElasticsearchStore",
    # Local / embedded
    "faiss": "vector_store.stores.faiss_store.FAISSStore",
    "chroma": "vector_store.stores.chroma_store.ChromaStore",
    # Cloud object store (hybrid FAISS + blob)
    "s3_vector": "vector_store.stores.s3_vector_store.S3VectorStore",
    "gcs_vector": "vector_store.stores.gcs_vector_store.GCSVectorStore",
    "azure_blob_vector": "vector_store.stores.azure_blob_vector_store.AzureBlobVectorStore",
}

# Object-store-backed types need an ObjectStoreConfig injected
_OBJECT_STORE_TYPES = {"s3_vector", "gcs_vector", "azure_blob_vector"}


@log_execution_time(logger)
def _import_class(dotted_path: str) -> Type[BaseVectorStore]:
    """Lazily import a class from a dotted module path."""
    import importlib

    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class VectorStoreFactory:
    """
    Factory for creating vector store backends from config.

    The factory is stateless — callers control instance lifecycle.
    Use a singleton / dependency-injection pattern in app code if reuse is needed.
    """

    @staticmethod
    @log_execution_time(logger)
    def create(config: dict) -> BaseVectorStore:
        """
        Instantiate a vector store from a raw config dict (parsed YAML).

        Reads config["vector_store"]["type"] to select the backend.
        For object-store-backed types also reads config["object_store"].

        Args:
            config: Full application config dict.

        Returns:
            A concrete BaseVectorStore (not yet connected).
            Call store.connect() or use it as a context manager.

        Raises:
            ValueError:  Unknown store type.
            ImportError: Required dependency not installed.
        """
        vs_config = VectorStoreConfig.from_config(config)
        store_type = vs_config.type.lower()
        logger.info(f"Vector store provider selected: {store_type}")

        if store_type not in _REGISTRY:
            supported = ", ".join(sorted(_REGISTRY.keys()))
            logger.warning(f"Unsupported vector store provider requested: {store_type}")
            raise ValueError(
                f"Unsupported vector store type: {store_type!r}.\n"
                f"Supported types: {supported}"
            )

        store_class = _import_class(_REGISTRY[store_type])
        logger.info(f"Creating vector store: {store_class.__name__}")

        logger.debug(
            f"Type={store_type}, "
            f"Collection={vs_config.collection_name}, "
            f"Index={vs_config.index.type}, "
            f"Strategy={vs_config.storage_strategy}"
        )

        if store_type in _OBJECT_STORE_TYPES:
            obj_config = ObjectStoreConfig.from_config(config)
            return store_class(vs_config, obj_config)

        return store_class(vs_config)

    @staticmethod
    @log_execution_time(logger)
    def create_from_yaml(yaml_path: str) -> BaseVectorStore:
        """
        Load config.yaml from disk and instantiate the store.

        Args:
            yaml_path: Path to the YAML config file.

        Returns:
            A concrete BaseVectorStore (not yet connected).
        """
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("PyYAML required → pip install pyyaml") from exc

        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return VectorStoreFactory.create(config)

    @staticmethod
    @log_execution_time(logger)
    def list_types() -> list[str]:
        """Return a sorted list of all registered store type keys."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    @log_execution_time(logger)
    def register(type_key: str, dotted_class_path: str) -> None:
        """
        Register a custom/third-party store backend at runtime.

        Args:
            type_key:          String key used in config.yaml
            dotted_class_path: e.g. "myapp.stores.MyCustomStore"

        Example:
            VectorStoreFactory.register(
                "my_db",
                "myapp.vector_store.MyDBStore"
            )
        """
        _REGISTRY[type_key.lower()] = dotted_class_path
        logger.info(f"Registered custom vector store provider: {type_key}")
