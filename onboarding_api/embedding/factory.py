from config.logger import setup_logger

logger = setup_logger(__name__)
from asyncio.log import logger
from typing import Type

from embedding.base import BaseEmbedder, EmbeddingConfig

# ── provider registry ──────────────────────────────────────────────────────────
# Maps config.embedding.provider → embedder class.
# Classes are imported lazily inside _REGISTRY to avoid pulling heavy
# dependencies (torch, transformers, etc.) unless the provider is actually used.

_REGISTRY: dict[str, str] = {
    # Commercial – dense text
    "openai": "embedding.providers.openai_embedder.OpenAIEmbedder",
    "azure_openai": "embedding.providers.azure_openai_embedder.AzureOpenAIEmbedder",
    "bedrock": "embedding.providers.bedrock_embedder.BedrockEmbedder",
    "google": "embedding.providers.google_vertex_embedder.GoogleVertexEmbedder",
    "cohere": "embedding.providers.cohere_embedder.CohereEmbedder",
    "voyage": "embedding.providers.voyage_embedder.VoyageEmbedder",
    "jina": "embedding.providers.jina_embedder.JinaEmbedder",
    # Open-source – dense text (local / self-hosted)
    "huggingface": "embedding.providers.huggingface_embedder.HuggingFaceEmbedder",
    "sentence_transformers": "embedding.providers.sentence_transformer_embedder.SentenceTransformerEmbedder",
    "instructor": "embedding.providers.instructor_embedder.InstructorEmbedder",
    "fastembed": "embedding.providers.fastembed_embedder.FastEmbedEmbedder",
    "ollama": "embedding.providers.ollama_embedder.OllamaEmbedder",
    # Sparse / lexical
    "splade": "embedding.providers.splade_embedder.SpladeEmbedder",
    "bm25": "embedding.providers.bm25_embedder.BM25Embedder",
    # Hybrid (dense + sparse)
    "hybrid": "embedding.providers.hybrid_embedder.HybridEmbedder",
    # Late interaction
    "colbert": "embedding.providers.colbert_embedder.ColBERTEmbedder",
    # Multimodal
    "clip": "embedding.providers.clip_embedder.CLIPEmbedder",
}


def _import_class(dotted_path: str) -> Type[BaseEmbedder]:
    """Lazily import a class from a dotted module path string."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class EmbeddingFactory:
    """
    Factory for creating embedding provider instances from config.

    The factory is intentionally stateless (no caching) so that callers
    control the object lifecycle.  Use a singleton pattern in your
    application layer if instance reuse is required.
    """

    @staticmethod
    def create(config: dict) -> BaseEmbedder:
        """
        Instantiate the appropriate embedder from a raw config dict.

        Args:
            config: Full application config dict.  The factory reads
                    config["embedding"]["provider"] to determine which
                    class to instantiate.

        Returns:
            A concrete BaseEmbedder instance.

        Raises:
            ValueError:  Unknown provider key.
            ImportError: Required package not installed for that provider.
        """
        embedding_config = EmbeddingConfig.from_config(config)
        provider = embedding_config.provider.lower()

        if provider not in _REGISTRY:
            supported = ", ".join(sorted(_REGISTRY.keys()))
            logger.warning(f"Unsupported embedding provider requested: {provider}")
            raise ValueError(
                f"Unsupported embedding provider: {provider!r}.\n"
                f"Supported providers: {supported}"
            )

        embedder_class = _import_class(_REGISTRY[provider])
        logger.info(f"Creating embedder: {embedder_class.__name__}")

        logger.debug(
            f"Provider={provider}, "
            f"Model={embedding_config.model}, "
            f"Type={embedding_config.type}, "
            f"Modality={embedding_config.modality}"
        )

        return embedder_class(embedding_config)

    @staticmethod
    def create_from_yaml(yaml_path: str) -> BaseEmbedder:
        """
        Load config.yaml from disk and instantiate the embedder.

        Args:
            yaml_path: Path to the YAML config file.

        Returns:
            A concrete BaseEmbedder instance.
        """
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("PyYAML required → pip install pyyaml") from exc

        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return EmbeddingFactory.create(config)

    @staticmethod
    def list_providers() -> list[str]:
        """Return a sorted list of all registered provider keys."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    def register(provider_key: str, dotted_class_path: str) -> None:
        """
        Register a custom/third-party embedder at runtime.

        Args:
            provider_key:       String key used in config.yaml
            dotted_class_path:  e.g. "mypackage.mymodule.MyEmbedder"

        Example:
            EmbeddingFactory.register(
                "my_custom",
                "myapp.embedders.custom.MyCustomEmbedder"
            )
        """
        _REGISTRY[provider_key.lower()] = dotted_class_path
        logger.info(f"Registered custom embedding provider: {provider_key}")
