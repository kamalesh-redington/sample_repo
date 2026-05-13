"""
Ollama Local Embedder
Provider key : "ollama"
Embedding type: dense
Modality     : text

Runs embedding models locally via the Ollama server.

Popular embedding models via Ollama:
    - nomic-embed-text   (768-dim)
    - mxbai-embed-large  (1024-dim)
    - all-minilm         (384-dim)
    - bge-m3             (1024-dim, multilingual)

Extra config fields:
    host : "http://localhost:11434"   (Ollama server URL)
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class OllamaEmbedder(BaseEmbedder):
    """Dense text embedder via locally running Ollama server."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import requests
        except ImportError as exc:
            raise ImportError("requests required → pip install requests") from exc

        import requests as _req
        self._session = _req.Session()
        self._host = config.extra.get("host", "http://localhost:11434")
        self._url = f"{self._host}/api/embed"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            payload = {"model": self.config.model, "input": batch}
            response = self._session.post(self._url, json=payload)
            response.raise_for_status()
            data = response.json()
            all_vectors.extend(data["embeddings"])

        return all_vectors
