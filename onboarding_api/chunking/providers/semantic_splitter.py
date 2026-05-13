"""
chunking/providers/semantic_splitter.py

Strategy: ``semantic``

Embedding-based semantic chunker: splits text at points of maximum semantic
dissimilarity between adjacent sentences, rather than at fixed size boundaries.

Algorithm (cosine-similarity breakpoints):
    1. Split text into sentences (punctuation-based).
    2. Embed each sentence using the configured embedding model.
    3. Compute cosine distance between each adjacent pair.
    4. Identify breakpoints where distance exceeds the Nth percentile threshold.
    5. Group sentences between breakpoints into chunks.

Config keys used
----------------
    chunking.chunk_size            : int   — soft max tokens (used to split very long chunks)
    chunking.embed_model           : str   — embedding provider key (defaults to "openai")
    chunking.breakpoint_percentile : int   — percentile threshold for split (default 95)
    embedding.*                    : dict  — full embedding config passed to EmbeddingFactory

Dependencies
------------
    Whatever SDK the chosen embed_model requires (e.g. openai, sentence-transformers).
    numpy is required for cosine similarity and percentile computation.
"""

import re
from typing import List

from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from chunking.base import BaseChunker, ChunkingConfig


class SemanticChunker(BaseChunker):
    """
    Splits documents at semantic breakpoints detected via embedding similarity.

    Falls back to ``SentenceChunker`` behaviour if no embedding model can be
    loaded (e.g. in tests or offline environments).
    """

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.breakpoint_percentile: int = config.breakpoint_percentile
        self._embedder = None   # lazily loaded on first call to chunk()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        """Naïve but fast sentence tokeniser using regex."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s for s in sentences if s.strip()]

    @staticmethod
    def _cosine_distance(a: List[float], b: List[float]) -> float:
        """Return 1 - cosine_similarity(a, b)."""
        try:
            import numpy as np  # type: ignore
            va, vb = np.array(a), np.array(b)
            denom = np.linalg.norm(va) * np.linalg.norm(vb)
            if denom == 0:
                return 1.0
            return float(1.0 - np.dot(va, vb) / denom)
        except ImportError:
            # Fallback pure-python dot product
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x ** 2 for x in a) ** 0.5
            norm_b = sum(x ** 2 for x in b) ** 0.5
            denom = norm_a * norm_b
            return 1.0 - (dot / denom) if denom else 1.0

    def _load_embedder(self, config: ChunkingConfig):
        """Lazily import EmbeddingFactory and create the embedder."""
        try:
            from embedding.factory import EmbeddingFactory  # type: ignore
            # Build a minimal embedding config from chunking config
            embed_config: dict = {
                "embedding": {
                    "provider": config.embed_model or "openai",
                    "model": config.extra.get("embed_model_name", "text-embedding-3-small"),
                    "type": "dense",
                    "modality": "text",
                    "dimensions": config.extra.get("dimensions", 1536),
                    "batch_size": config.extra.get("batch_size", 32),
                    "normalize": True,
                }
            }
            return EmbeddingFactory.create(embed_config)
        except Exception as exc:
            print(
                f"[SemanticChunker] Could not load embedder: {exc}. "
                f"Falling back to sentence splitting."
            )
            return None

    def _find_breakpoints(self, embeddings: List[List[float]]) -> List[int]:
        """Return indices (in the sentence list) that are split points."""
        if len(embeddings) < 2:
            return []

        distances = [
            self._cosine_distance(embeddings[i], embeddings[i + 1])
            for i in range(len(embeddings) - 1)
        ]

        try:
            import numpy as np  # type: ignore
            threshold = float(np.percentile(distances, self.breakpoint_percentile))
        except ImportError:
            sorted_d = sorted(distances)
            idx = int(len(sorted_d) * self.breakpoint_percentile / 100)
            threshold = sorted_d[min(idx, len(sorted_d) - 1)]

        return [i for i, d in enumerate(distances) if d >= threshold]

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, documents: List[Document]) -> List[BaseNode]:
        """
        Split documents at semantic boundaries detected by embedding similarity.
        """
        if self._embedder is None:
            self._embedder = self._load_embedder(self.config)

        nodes: List[BaseNode] = []

        for doc in documents:
            text = doc.text or ""
            sentences = self._sentence_split(text)

            if not sentences:
                continue

            # If no embedder available, fall back to single-chunk pass-through
            if self._embedder is None:
                nodes.append(
                    TextNode(
                        text=text,
                        metadata={**doc.metadata, "chunk_index": 0},
                        id_=f"{doc.doc_id}_sem_0",
                    )
                )
                continue

            # Embed all sentences
            try:
                embeddings = self._embedder.embed_texts(sentences)
            except Exception as exc:
                print(f"[SemanticChunker] Embedding failed for doc {doc.doc_id}: {exc}")
                nodes.append(
                    TextNode(
                        text=text,
                        metadata={**doc.metadata, "chunk_index": 0},
                        id_=f"{doc.doc_id}_sem_0",
                    )
                )
                continue

            # Find split points
            breakpoints = set(self._find_breakpoints(embeddings))

            # Group sentences into chunks
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

            # Flush remaining sentences
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

        print(
            f"[SemanticChunker] {len(documents)} document(s) → "
            f"{len(nodes)} semantic chunk(s) "
            f"(breakpoint_percentile={self.breakpoint_percentile})"
        )
        return nodes
