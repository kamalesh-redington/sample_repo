from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EmbeddingConfig:
    """
    Unified config dataclass derived from config.yaml → embedding section.

    Fields mirror the YAML schema:
        embedding:
          provider: openai
          model: text-embedding-3-small
          type: dense                  # dense | sparse | hybrid | late_interaction | instructor
          modality: text               # text | image | multimodal | audio | molecular
          dimensions: 1536
          batch_size: 32
          normalize: true
          pooling: mean                # mean | cls | max
          instruction: ""             # optional instruction prefix
    """

    provider: str                          # e.g. "openai", "cohere", "voyage", ...
    model: str                             # e.g. "text-embedding-3-small"
    type: str = "dense"                    # embedding strategy type
    modality: str = "text"                 # input modality
    dimensions: int = 1536                 # output vector size
    batch_size: int = 32                   # how many texts to embed per API call
    normalize: bool = True                 # L2-normalize output vectors
    pooling: str = "mean"                  # pooling strategy for token-based models
    instruction: Optional[str] = None      # instruction prefix (instructor-type models)

    # Provider-specific extras (passed through transparently)
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "EmbeddingConfig":
        """Build EmbeddingConfig from a raw config dict (parsed YAML)."""
        emb = config.get("embedding", {})
        known_keys = {
            "provider", "model", "type", "modality",
            "dimensions", "batch_size", "normalize", "pooling", "instruction",
        }
        extra = {k: v for k, v in emb.items() if k not in known_keys}
        return cls(
            provider=emb["provider"],
            model=emb.get("model", ""),
            type=emb.get("type", "dense"),
            modality=emb.get("modality", "text"),
            dimensions=emb.get("dimensions", 1536),
            batch_size=emb.get("batch_size", 32),
            normalize=emb.get("normalize", True),
            pooling=emb.get("pooling", "mean"),
            instruction=emb.get("instruction"),
            extra=extra,
        )


class BaseEmbedder(ABC):
    """
    Abstract base for every embedding provider.

    All concrete embedders MUST implement:
        embed_texts(texts)  → List[List[float]]

    And MAY override:
        embed_query(text)   → List[float]   (single query shortcut)
        info()              → dict          (provider metadata)
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts in batches.

        Args:
            texts: Raw text strings to embed.

        Returns:
            Parallel list of float vectors (one per text).
        """

    def embed_query(self, text: str) -> List[float]:
        """Convenience wrapper — embed a single query string."""
        return self.embed_texts([text])[0]

    def info(self) -> dict:
        """Return provider metadata dict (useful for logging / debugging)."""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "type": self.config.type,
            "modality": self.config.modality,
            "dimensions": self.config.dimensions,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider={self.config.provider!r}, "
            f"model={self.config.model!r}, "
            f"type={self.config.type!r})"
        )
