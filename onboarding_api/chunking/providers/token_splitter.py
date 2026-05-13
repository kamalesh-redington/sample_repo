"""
chunking/providers/token_splitter.py

Strategy: ``token``

Wraps LlamaIndex's ``TokenTextSplitter`` which splits text purely by token
count using the tiktoken tokenizer (or a Hugging Face tokenizer if configured).

Config keys used
----------------
    chunking.chunk_size    : int — max tokens per chunk (default 512)
    chunking.chunk_overlap : int — token overlap between chunks (default 64)
"""

from typing import List

from llama_index.core import Document
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import BaseNode

from chunking.base import BaseChunker, ChunkingConfig


class TokenChunker(BaseChunker):
    """
    Splits documents into fixed-size token windows.

    Uses LlamaIndex ``TokenTextSplitter`` backed by the ``cl100k_base``
    tiktoken tokenizer (same as OpenAI ``text-embedding-3-*`` models).

    Ideal when you need strict, predictable token budgets.
    """

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self._splitter = TokenTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def chunk(self, documents: List[Document]) -> List[BaseNode]:
        """Split documents into token-bounded nodes."""
        nodes = self._splitter.get_nodes_from_documents(documents)
        print(
            f"[TokenChunker] {len(documents)} document(s) → "
            f"{len(nodes)} node(s)"
        )
        return nodes
