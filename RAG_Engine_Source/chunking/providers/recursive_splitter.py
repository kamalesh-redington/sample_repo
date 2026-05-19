"""
chunking/providers/recursive_splitter.py

Strategy: ``recursive``

Implements LangChain-style recursive character splitting: tries a sequence of
separator characters in priority order, falling back to the next separator
when a chunk is still too large.  This preserves paragraph → sentence →
word structure as long as possible.

Config keys used
----------------
    chunking.chunk_size    : int         — max characters per chunk (default 512)
    chunking.chunk_overlap : int         — character overlap (default 64)
    chunking.extra.separators : list[str] — override default separator list

Default separator priority
--------------------------
    "\\n\\n"  → paragraph boundary (highest priority)
    "\\n"     → line boundary
    ". "     → sentence boundary
    " "      → word boundary
    ""       → character fallback (lowest priority)
"""

from typing import List

from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from chunking.base import BaseChunker, ChunkingConfig

_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class RecursiveChunker(BaseChunker):
    """
    Recursively splits text using a priority-ordered list of separators.

    Mimics ``langchain.text_splitter.RecursiveCharacterTextSplitter`` but is
    implemented here without requiring the LangChain dependency.

    The algorithm:
        1. Try the first separator.
        2. If any resulting segment is still larger than ``chunk_size``,
           recursively apply the next separator to that segment.
        3. Combine small adjacent segments with overlap.
    """

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.chunk_size: int = config.chunk_size
        self.chunk_overlap: int = min(config.chunk_overlap, config.chunk_size - 1)
        self.separators: List[str] = config.extra.get(
            "separators", _DEFAULT_SEPARATORS
        )

    # ------------------------------------------------------------------
    # Core splitting logic
    # ------------------------------------------------------------------

    def _split(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using the separator priority list."""
        if not text:
            return []

        sep = separators[0]
        next_seps = separators[1:]

        # Split on the current separator (empty-string = char-by-char)
        if sep == "":
            raw_parts = list(text)
        else:
            raw_parts = text.split(sep)

        # Re-attach separator (except for fallback) and recurse big pieces
        pieces: List[str] = []
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= self.chunk_size:
                pieces.append(part)
            elif next_seps:
                pieces.extend(self._split(part, next_seps))
            else:
                # Brute-force character fallback
                for i in range(0, len(part), self.chunk_size - self.chunk_overlap):
                    pieces.append(part[i : i + self.chunk_size])

        return self._merge(pieces)

    def _merge(self, pieces: List[str]) -> List[str]:
        """Combine adjacent small pieces into chunks, respecting overlap."""
        chunks: List[str] = []
        current = ""

        for piece in pieces:
            candidate = (current + " " + piece).strip() if current else piece
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # Carry overlap forward
                if self.chunk_overlap > 0 and len(current) >= self.chunk_overlap:
                    current = current[-self.chunk_overlap :] + " " + piece
                else:
                    current = piece

        if current:
            chunks.append(current)

        return chunks

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, documents: List[Document]) -> List[BaseNode]:
        """Split documents recursively and return TextNode list."""
        nodes: List[BaseNode] = []

        for doc in documents:
            text = doc.text or ""
            chunks = self._split(text, self.separators)

            for i, chunk_text in enumerate(chunks):
                meta = {**doc.metadata, "chunk_index": i}
                node = TextNode(
                    text=chunk_text,
                    metadata=meta,
                    id_=f"{doc.doc_id}_rec_{i}",
                )
                nodes.append(node)

        print(
            f"[RecursiveChunker] {len(documents)} document(s) → "
            f"{len(nodes)} node(s) "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return nodes
