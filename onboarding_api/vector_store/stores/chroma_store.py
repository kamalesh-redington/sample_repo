from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore,
    QueryResult,
    VectorDocument,
    VectorStoreConfig
)


class ChromaStore(BaseVectorStore):

    def __init__(self, config: VectorStoreConfig):

        super().__init__(config)

        logger.info(
            "Initializing ChromaStore"
        )

        self._client = None
        self._collection = None

    def connect(self) -> None:

        try:

            logger.info(
                "Connecting to ChromaDB"
            )

            import chromadb

        except ImportError as exc:

            logger.exception(
                "chromadb import failed"
            )

            raise ImportError(
                "chromadb required → pip install chromadb"
            ) from exc

        import chromadb

        persist_dir = self.config.extra.get(
            "persist_directory",
            "./chroma_db"
        )

        logger.debug(
            f"Chroma persistence directory: {persist_dir}"
        )

        self._client = chromadb.PersistentClient(
            path=persist_dir
        )

        self._collection = (
            self._client.get_or_create_collection(
                name=self.config.collection_name
            )
        )

        logger.info(
            "Connected to ChromaDB successfully"
        )

    def close(self) -> None:

        logger.info(
            "Closing ChromaDB connection"
        )

        self._client = None

    def upsert(
        self,
        documents: List[VectorDocument]
    ) -> None:

        try:

            logger.info(
                f"Starting ChromaDB upsert for {len(documents)} documents"
            )

            self._collection.upsert(
                ids=[d.id for d in documents],
                embeddings=[d.vector for d in documents],
                documents=[d.text for d in documents],
                metadatas=[d.metadata for d in documents],
            )

            logger.info(
                "ChromaDB upsert completed successfully"
            )

        except Exception as e:

            logger.exception(
                "ChromaDB upsert failed"
            )

            raise

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:

        try:

            logger.info(
                "Starting ChromaDB query"
            )

            results = self._collection.query(
                query_embeddings=[vector],
                n_results=top_k or self.config.query_top_k,
            )

            response = []

            for i in range(
                len(results["ids"][0])
            ):

                response.append(
                    QueryResult(
                        id=results["ids"][0][i],
                        score=float(
                            results["distances"][0][i]
                        ),
                        text=results["documents"][0][i],
                        metadata=results["metadatas"][0][i],
                    )
                )

            logger.info(
                f"ChromaDB query returned {len(response)} results"
            )

            return response

        except Exception as e:

            logger.exception(
                "ChromaDB query failed"
            )

            raise

    def delete(
        self,
        ids: List[str]
    ) -> None:

        try:

            logger.info(
                f"Deleting {len(ids)} vectors from ChromaDB"
            )

            self._collection.delete(ids=ids)

            logger.info(
                "ChromaDB delete completed successfully"
            )

        except Exception as e:

            logger.exception(
                "ChromaDB delete failed"
            )

            raise