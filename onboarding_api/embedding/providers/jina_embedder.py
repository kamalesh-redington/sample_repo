"""
Jina AI Embedder
Provider key : "jina"
Embedding type: dense | late_interaction
Modality     : text | multimodal

Supported models:
    - jina-embeddings-v3           (1024-dim, multilingual, text)
    - jina-clip-v2                 (1024-dim, text+image multimodal)
    - jina-colbert-v2              (late_interaction, token-level)

Extra config fields:
    api_key    : Jina API key (or env JINA_API_KEY)
    task       : "retrieval.passage" | "retrieval.query" | "text-matching"
"""

import os
from typing import List, Union

from embedding.base import BaseEmbedder, EmbeddingConfig


class JinaEmbedder(BaseEmbedder):
    """
    Dense / multimodal / late-interaction embedder via Jina AI REST API.

    For jina-colbert-v2 (type=late_interaction), embed_texts returns
    token-level embeddings as a flat list of per-text lists (each inner
    list is a list of token vectors).  The standard interface returns
    the single CLS/mean vector for compatibility.
    """

    _BASE_URL = "https://api.jina.ai/v1/embeddings"

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import requests
        except ImportError as exc:
            raise ImportError(
                "requests is required → pip install requests"
            ) from exc

        self._session = requests.Session()
        api_key = config.extra.get("api_key") or os.environ.get("JINA_API_KEY", "")
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )
        self._task = config.extra.get("task", "retrieval.passage")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            payload = {
                "model": self.config.model,
                "input": batch,
                "task": self._task,
                "dimensions": self.config.dimensions or None,
                "normalized": self.config.normalize,
            }
            response = self._session.post(self._BASE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            for item in data["data"]:
                all_vectors.append(item["embedding"])

        return all_vectors
