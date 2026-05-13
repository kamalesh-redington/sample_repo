"""
chunking/providers/character_splitter.py

Strategy: ``character``

Pure character-level fixed-size windowing with overlap.  Does not require
any tokenizer, making it useful for non-English text or custom tokenization
schemes.

Config keys used
----------------
    chunking.chunk_size    : int — max characters per chunk (default 512)
    chunking.chunk_overlap : int — character overlap between chunks (default 64)
"""

from typing import List

from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from chunking.base import BaseChunker, ChunkingConfig


class CharacterChunker(BaseChunker):
    """
    Splits documents into fixed-size character windows.

    Unlike ``TokenChunker``, this operates directly on raw character counts,
    making it fast, tokenizer-agnostic, and suitable for any language or
    binary-safe text representation.

    Metadata from the source document is propagated to every child node.
    """

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.chunk_size: int = config.chunk_size
        self.chunk_overlap: int = min(config.chunk_overlap, config.chunk_size - 1)

    def _split_text(self, text: str) -> List[str]:
        """Slide a window of ``chunk_size`` chars across ``text``."""
        chunks: List[str] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += step
            if start >= len(text):
                break
        return chunks

    def chunk(self, documents: List[Document]) -> List[BaseNode]:
        """Split documents into fixed-size character nodes."""
        nodes: List[BaseNode] = []

        for doc in documents:
            text = doc.text or ""
            chunks = self._split_text(text)

            for i, chunk_text in enumerate(chunks):
                meta = {**doc.metadata, "chunk_index": i}
                node = TextNode(
                    text=chunk_text,
                    metadata=meta,
                    id_=f"{doc.doc_id}_char_{i}",
                )
                nodes.append(node)

        print(
            f"[CharacterChunker] {len(documents)} document(s) → "
            f"{len(nodes)} node(s) "
            f"(size={self.chunk_size} chars, overlap={self.chunk_overlap} chars)"
        )
        return nodes
