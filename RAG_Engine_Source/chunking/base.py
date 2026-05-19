"""
chunking/base.py — Abstract base class and config dataclass for all chunkers.

Every concrete chunker in ``chunking/providers/`` MUST inherit from
``BaseChunker`` and implement the ``chunk()`` method.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from llama_index.core import Document
from llama_index.core.schema import BaseNode


@dataclass
class ChunkingConfig:
    """
    Unified config for text chunking, derived from config.yaml → chunking section.

    YAML schema::

        chunking:
          strategy: sentence    # sentence | token | character | recursive | semantic
          chunk_size: 512       # target size (tokens, chars, or sentences depending on strategy)
          chunk_overlap: 64     # overlap between consecutive chunks
          split_by: token       # token | sentence | character  (for strategy=sentence)
          handle_images: true   # passed through to image-aware extractors
          # semantic-only options:
          # embed_model: openai
          # breakpoint_percentile: 95
    """

    strategy: str = "sentence"          # chunking strategy key
    chunk_size: int = 512               # tokens / chars per chunk
    chunk_overlap: int = 64             # overlap between chunks
    split_by: str = "token"            # used by sentence strategy
    handle_images: bool = True          # pass-through flag for extractors

    # Semantic chunker extras
    embed_model: Optional[str] = None
    breakpoint_percentile: int = 95

    # Any unknown keys are kept here for provider-specific use
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "ChunkingConfig":
        """Build a ChunkingConfig from a raw application config dict."""
        chunk_cfg = config.get("chunking", {})
        known_keys = {
            "strategy", "chunk_size", "chunk_overlap",
            "split_by", "handle_images", "embed_model", "breakpoint_percentile",
        }
        extra = {k: v for k, v in chunk_cfg.items() if k not in known_keys}
        return cls(
            strategy=chunk_cfg.get("strategy", "sentence"),
            chunk_size=chunk_cfg.get("chunk_size", 512),
            chunk_overlap=chunk_cfg.get("chunk_overlap", 64),
            split_by=chunk_cfg.get("split_by", "token"),
            handle_images=chunk_cfg.get("handle_images", True),
            embed_model=chunk_cfg.get("embed_model"),
            breakpoint_percentile=chunk_cfg.get("breakpoint_percentile", 95),
            extra=extra,
        )


class BaseChunker(ABC):
    """
    Abstract base class for every chunking strategy.

    All concrete chunkers MUST implement:
        chunk(documents) → List[BaseNode]

    Chunkers receive a list of LlamaIndex ``Document`` objects and return
    a list of ``BaseNode`` objects ready for embedding and indexing.
    """

    def __init__(self, config: ChunkingConfig):
        self.config = config

    @abstractmethod
    def chunk(self, documents: List[Document]) -> List[BaseNode]:
        """
        Split documents into nodes/chunks.

        Args:
            documents: List of LlamaIndex Document objects.

        Returns:
            List of BaseNode objects (TextNode, ImageNode, etc.).
        """

    def info(self) -> dict:
        """Return chunker metadata for logging."""
        return {
            "strategy": self.config.strategy,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"strategy={self.config.strategy!r}, "
            f"chunk_size={self.config.chunk_size}, "
            f"chunk_overlap={self.config.chunk_overlap})"
        )
