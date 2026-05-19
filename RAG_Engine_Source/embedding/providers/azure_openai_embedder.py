"""
Azure OpenAI Dense Embedder
Provider key : "azure_openai"
Embedding type: dense
Modality     : text

Extra config fields (under embedding.extra / YAML siblings):
    azure_endpoint : "https://<resource>.openai.azure.com/"
    azure_api_key  : "<key>"               (or env AZURE_OPENAI_API_KEY)
    api_version    : "2024-02-01"
    deployment     : "text-embedding-3-small"  (Azure deployment name)
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class AzureOpenAIEmbedder(BaseEmbedder):
    """Dense text embedder backed by Azure-hosted OpenAI."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is required → pip install openai"
            ) from exc

        self._client = AzureOpenAI(
            azure_endpoint=config.extra.get("azure_endpoint"),
            api_key=config.extra.get("azure_api_key"),
            api_version=config.extra.get("api_version", "2024-02-01"),
        )
        self._deployment = config.extra.get("deployment", config.model)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            response = self._client.embeddings.create(
                model=self._deployment,
                input=batch,
            )
            for item in response.data:
                all_vectors.append(item.embedding)

        return all_vectors
