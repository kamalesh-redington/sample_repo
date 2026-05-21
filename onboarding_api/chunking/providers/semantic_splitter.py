from config.logger import setup_logger

logger = setup_logger(__name__)

import re

from typing import List

from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from chunking.base import BaseChunker, ChunkingConfig


class SemanticChunker(BaseChunker):

    def __init__(self, config: ChunkingConfig):

        super().__init__(config)

        self.breakpoint_percentile: int = config.breakpoint_percentile

        self._embedder = None

        logger.info("Initializing SemanticChunker")

        logger.debug(f"Breakpoint percentile: {self.breakpoint_percentile}")

    @staticmethod
    def _sentence_split(text: str) -> List[str]:

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        sentences = [s for s in sentences if s.strip()]

        logger.debug(f"Semantic sentence count: {len(sentences)}")

        return sentences

    @staticmethod
    def _cosine_distance(a: List[float], b: List[float]) -> float:

        try:

            import numpy as np

            va, vb = np.array(a), np.array(b)

            denom = np.linalg.norm(va) * np.linalg.norm(vb)

            if denom == 0:
                return 1.0

            return float(1.0 - np.dot(va, vb) / denom)

        except ImportError:

            dot = sum(x * y for x, y in zip(a, b))

            norm_a = sum(x**2 for x in a) ** 0.5

            norm_b = sum(x**2 for x in b) ** 0.5

            denom = norm_a * norm_b

            return 1.0 - (dot / denom) if denom else 1.0

    def _load_embedder(self, config: ChunkingConfig):

        try:

            logger.info("Loading embedding model for semantic chunking")

            from embedding.factory import EmbeddingFactory

            embed_config: dict = {
                "embedding": {
                    "provider": config.embed_model or "openai",
                    "model": config.extra.get(
                        "embed_model_name", "text-embedding-3-small"
                    ),
                    "type": "dense",
                    "modality": "text",
                    "dimensions": config.extra.get("dimensions", 1536),
                    "batch_size": config.extra.get("batch_size", 32),
                    "normalize": True,
                }
            }

            embedder = EmbeddingFactory.create(embed_config)

            logger.info("Semantic embedder loaded successfully")

            return embedder

        except Exception as exc:

            logger.warning(f"Semantic embedder unavailable, fallback enabled: {exc}")

            return None

    def _find_breakpoints(self, embeddings: List[List[float]]) -> List[int]:

        if len(embeddings) < 2:
            return []

        distances = [
            self._cosine_distance(embeddings[i], embeddings[i + 1])
            for i in range(len(embeddings) - 1)
        ]

        logger.debug(f"Semantic breakpoint count: {len(distances)}")

        try:

            import numpy as np

            threshold = float(np.percentile(distances, self.breakpoint_percentile))

        except ImportError:

            sorted_d = sorted(distances)

            idx = int(len(sorted_d) * self.breakpoint_percentile / 100)

            threshold = sorted_d[min(idx, len(sorted_d) - 1)]

        return [i for i, d in enumerate(distances) if d >= threshold]

    def chunk(self, documents: List[Document]) -> List[BaseNode]:

        try:

            logger.info(f"Starting semantic chunking for {len(documents)} document(s)")

            if self._embedder is None:

                self._embedder = self._load_embedder(self.config)

            nodes: List[BaseNode] = []

            for doc in documents:

                text = doc.text or ""

                sentences = self._sentence_split(text)

                logger.debug(f"Semantic sentence count for document: {len(sentences)}")

                if not sentences:
                    continue

                if self._embedder is None:

                    logger.warning("Semantic embedder unavailable, using fallback")

                    nodes.append(
                        TextNode(
                            text=text,
                            metadata={**doc.metadata, "chunk_index": 0},
                            id_=f"{doc.doc_id}_sem_0",
                        )
                    )

                    continue

                try:

                    logger.info("Generating semantic embeddings")

                    embeddings = self._embedder.embed_texts(sentences)

                    logger.debug(f"Generated embeddings count: {len(embeddings)}")

                except Exception as exc:

                    logger.exception(
                        f"Semantic embedding failed for document: {doc.doc_id}"
                    )

                    nodes.append(
                        TextNode(
                            text=text,
                            metadata={**doc.metadata, "chunk_index": 0},
                            id_=f"{doc.doc_id}_sem_0",
                        )
                    )

                    continue

                breakpoints = set(self._find_breakpoints(embeddings))

                logger.debug(f"Detected semantic breakpoints: {len(breakpoints)}")

                current_sentences: List[str] = []

                chunk_idx = 0

                for i, sentence in enumerate(sentences):

                    current_sentences.append(sentence)

                    if i in breakpoints:

                        chunk_text = " ".join(current_sentences).strip()

                        if chunk_text:

                            nodes.append(
                                TextNode(
                                    text=chunk_text,
                                    metadata={**doc.metadata, "chunk_index": chunk_idx},
                                    id_=f"{doc.doc_id}_sem_{chunk_idx}",
                                )
                            )

                            chunk_idx += 1

                        current_sentences = []

                if current_sentences:

                    chunk_text = " ".join(current_sentences).strip()

                    if chunk_text:

                        nodes.append(
                            TextNode(
                                text=chunk_text,
                                metadata={**doc.metadata, "chunk_index": chunk_idx},
                                id_=f"{doc.doc_id}_sem_{chunk_idx}",
                            )
                        )

            logger.info("Semantic chunking completed successfully")

            logger.debug(f"Generated semantic nodes: {len(nodes)}")

            return nodes

        except Exception as e:

            logger.exception("Semantic chunking failed")

            raise
