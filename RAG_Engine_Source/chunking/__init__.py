"""
chunking — factory-based text chunking module.

Public API
----------
    from chunking.factory import ChunkingFactory

    chunker = ChunkingFactory.create(config)
    nodes   = chunker.chunk(documents)

Available strategies (config.chunking.strategy)
------------------------------------------------
    sentence   → SentenceChunker   wraps LlamaIndex SentenceSplitter
    token      → TokenChunker      wraps LlamaIndex TokenTextSplitter
    character  → CharacterChunker  fixed-size character windows
    recursive  → RecursiveChunker  LangChain-style recursive splitting
    semantic   → SemanticChunker   embedding-based semantic boundaries
"""

# Lazy imports — heavy deps (llama_index, torch) are only pulled in
# when the caller explicitly imports from the submodules.

__all__ = ["ChunkingFactory", "BaseChunker", "ChunkingConfig"]
