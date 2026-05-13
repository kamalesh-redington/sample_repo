"""
chunking/providers/sentence_splitter.py

Strategy: ``sentence``

Wraps LlamaIndex's ``SentenceSplitter`` which splits text at natural sentence
boundaries while still respecting a maximum token budget per chunk.

Config keys used
----------------
    chunking.chunk_size    : int  — max tokens per chunk (default 512)
    chunking.chunk_overlap : int  — token overlap between chunks (default 64)
"""

from typing import List

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode

from chunking.base import BaseChunker, ChunkingConfig


class SentenceChunker(BaseChunker):
    """
    Splits documents into chunks at sentence boundaries.

    Uses LlamaIndex ``SentenceSplitter`` under the hood, which tries to
    keep sentences intact while honoring ``chunk_size`` (in tokens).
    """

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self._splitter = SentenceSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def chunk(self, documents: List[Document]) -> List[BaseNode]:
        """Split documents into sentence-boundary-respecting nodes."""
        nodes = self._splitter.get_nodes_from_documents(documents)
        print(
            f"[SentenceChunker] {len(documents)} document(s) -> "
            f"{len(nodes)} node(s)"
        )
        return nodes
