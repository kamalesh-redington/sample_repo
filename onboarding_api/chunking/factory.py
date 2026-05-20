"""
ChunkingFactory — config-driven chunking strategy instantiation.

Usage
-----
    from chunking.factory import ChunkingFactory

    chunker = ChunkingFactory.create(config)
    nodes   = chunker.chunk(documents)

Supported strategies (config.chunking.strategy)
-----------------------------------------------
    sentence   → SentenceChunker   wraps LlamaIndex SentenceSplitter
    token      → TokenChunker      wraps LlamaIndex TokenTextSplitter
    character  → CharacterChunker  fixed-size character windows
    recursive  → RecursiveChunker  LangChain-style recursive splitting
    semantic   → SemanticChunker   embedding-based semantic boundaries
"""

import importlib
from typing import Type
from config.logger import setup_logger
logger = setup_logger(__name__)
from chunking.base import BaseChunker, ChunkingConfig

# ── Registry: strategy key → dotted class path ────────────────────────────────
# Imports are deferred so heavy deps (torch, sentence-transformers) are only
# loaded if the corresponding strategy is actually configured.

_REGISTRY: dict[str, str] = {
    "sentence": "chunking.providers.sentence_splitter.SentenceChunker",
    "token": "chunking.providers.token_splitter.TokenChunker",
    "character": "chunking.providers.character_splitter.CharacterChunker",
    "recursive": "chunking.providers.recursive_splitter.RecursiveChunker",
    "semantic": "chunking.providers.semantic_splitter.SemanticChunker",
}


def _import_class(dotted_path: str) -> Type[BaseChunker]:
    """Lazily import a BaseChunker subclass from a dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class ChunkingFactory:
    """
    Factory for creating chunking strategy instances from config.

    Stateless by design — the application layer controls instance lifecycle.
    """

    @staticmethod
    def create(config: dict) -> BaseChunker:
        """
        Instantiate the appropriate chunker from a raw config dict.

        Args:
            config: Full application config dict.  The factory reads
                    ``config["chunking"]["strategy"]`` to select the class.
                    Defaults to ``"sentence"`` if the key is absent.

        Returns:
            A concrete BaseChunker instance.

        Raises:
            ValueError:  Unknown strategy key.
            ImportError: Required package not installed for that strategy.
        """
        logger.info("Initializing chunking configuration")
        chunking_cfg = ChunkingConfig.from_config(config)
        strategy = chunking_cfg.strategy.lower().strip()
        logger.info(f"Chunking strategy selected: {strategy}")

        logger.debug(
            f"Chunk size: {chunking_cfg.chunk_size}, "
            f"Chunk overlap: {chunking_cfg.chunk_overlap}"
        )
        if strategy not in _REGISTRY:
            supported = ", ".join(sorted(_REGISTRY.keys()))
            logger.warning(f"Unsupported chunking strategy requested: {strategy}")
            raise ValueError(
                f"Unsupported chunking strategy: {strategy!r}.\n"
                f"Supported strategies: {supported}"
            )

        chunker_class = _import_class(_REGISTRY[strategy])
        logger.info(f"Creating chunker: {chunker_class.__name__}")

        logger.debug(
            f"Chunker configuration -> "
            f"strategy={strategy}, "
            f"chunk_size={chunking_cfg.chunk_size}, "
            f"chunk_overlap={chunking_cfg.chunk_overlap}"
        )
        logger.info(f"Chunker initialized successfully: {chunker_class.__name__}")
        return chunker_class(chunking_cfg)

    @staticmethod
    def list_strategies() -> list[str]:
        """Return a sorted list of all registered strategy keys."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    def register(strategy_key: str, dotted_class_path: str) -> None:
        """
        Register a custom chunking strategy at runtime.

        Args:
            strategy_key:       Key used in ``config.yaml`` (e.g. ``"sliding_window"``)
            dotted_class_path:  e.g. ``"mypackage.chunkers.SlidingWindowChunker"``

        Example::

            ChunkingFactory.register(
                "sliding_window",
                "myapp.chunkers.sliding.SlidingWindowChunker"
            )
        """
        _REGISTRY[strategy_key.lower()] = dotted_class_path
        logger.info(f"Registered custom chunking strategy: {strategy_key}")
