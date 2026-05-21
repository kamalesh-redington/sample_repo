from config.logger import setup_logger

logger = setup_logger(__name__)

import os
import pickle

from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore,
    QueryResult,
    VectorDocument,
    VectorStoreConfig,
)


class FAISSStore(BaseVectorStore):

    def __init__(self, config: VectorStoreConfig):

        super().__init__(config)

        logger.info("Initializing FAISSStore")

        self._index = None

        self._documents = {}

        self._index_path = config.extra.get("index_path", "faiss.index")

        logger.debug(f"FAISS index path: {self._index_path}")

    def connect(self) -> None:

        try:

            logger.info("Connecting to FAISS")

            import faiss
            import numpy as np

        except ImportError as exc:

            logger.exception("faiss import failed")

            raise ImportError("faiss-cpu required → pip install faiss-cpu") from exc

        dimension = self.config.extra.get("dimensions", 1536)

        logger.debug(f"FAISS dimensions: {dimension}")

        self._index = faiss.IndexFlatL2(dimension)

        logger.info("FAISS index initialized successfully")

    def close(self) -> None:

        logger.info("Closing FAISS store")

        self._index = None

    def upsert(self, documents: List[VectorDocument]) -> None:

        try:

            import numpy as np

            logger.info(f"Starting FAISS upsert for {len(documents)} documents")

            vectors = []

            for doc in documents:

                vectors.append(doc.vector)

                self._documents[len(self._documents)] = doc

            vectors_np = np.array(vectors, dtype="float32")

            self._index.add(vectors_np)

            logger.info("FAISS upsert completed successfully")

            logger.debug(f"FAISS vector count: {self._index.ntotal}")

        except Exception as e:

            logger.exception("FAISS upsert failed")

            raise

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:

        try:

            import numpy as np

            logger.info("Starting FAISS vector query")

            k = top_k or self.config.query_top_k

            logger.debug(f"FAISS top_k: {k}")

            query_np = np.array([vector], dtype="float32")

            distances, indices = self._index.search(query_np, k)

            results = []

            for score, idx in zip(distances[0], indices[0]):

                if idx == -1:
                    continue

                doc = self._documents[idx]

                results.append(
                    QueryResult(
                        id=doc.id,
                        score=float(score),
                        text=doc.text,
                        metadata=doc.metadata,
                    )
                )

            logger.info(f"FAISS query returned {len(results)} results")

            return results

        except Exception as e:

            logger.exception("FAISS query failed")

            raise

    def delete(self, ids: List[str]) -> None:

        logger.warning("FAISS delete operation not supported directly")

    def persist(self) -> None:

        try:

            import faiss

            logger.info("Persisting FAISS index")

            faiss.write_index(self._index, self._index_path)

            with open(self._index_path + ".meta", "wb") as f:

                pickle.dump(self._documents, f)

            logger.info("FAISS persistence completed successfully")

        except Exception as e:

            logger.exception("FAISS persistence failed")

            raise
