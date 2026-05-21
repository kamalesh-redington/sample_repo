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
    "cosine": "Cosine",
    "l2": "Euclid",
    "dot_product": "Dot",
}


class QdrantStore(BaseVectorStore):

    def __init__(self, config: VectorStoreConfig):

        super().__init__(config)

        logger.info("Initializing QdrantStore")

        self._client = None

    # ─────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────

    def connect(self) -> None:

        try:

            logger.info("Connecting to Qdrant")

            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

        except ImportError as exc:

            logger.exception("qdrant-client import failed")
