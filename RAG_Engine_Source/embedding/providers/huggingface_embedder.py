"""
HuggingFace Dense Embedder
Provider key : "huggingface"
Embedding type: dense
Modality     : text

Uses HuggingFace Inference API (hosted) OR local pipeline.

Extra config fields:
    api_key       : HF token (or env HUGGINGFACE_API_KEY)
    use_local     : false   → use Inference API; true → run locally
    device        : "cpu" | "cuda" | "mps"
    pooling       : overrides config.pooling if needed
"""

import os
from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class HuggingFaceEmbedder(BaseEmbedder):
    """Dense text embedder using HuggingFace Inference API or a local pipeline."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._use_local: bool = config.extra.get("use_local", False)

        if self._use_local:
            self._init_local(config)
        else:
            self._init_api(config)

    # ── local (transformers) ──────────────────────────────────────────────────

    def _init_local(self, config: EmbeddingConfig):
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch
        except ImportError as exc:
            raise ImportError(
                "transformers + torch required → pip install transformers torch"
            ) from exc

        import torch
        from transformers import AutoModel, AutoTokenizer

        device = config.extra.get("device", "cpu")
        self._device = torch.device(device)
        self._tokenizer = AutoTokenizer.from_pretrained(config.model)
        self._model = AutoModel.from_pretrained(config.model).to(self._device)
        self._model.eval()

    def _local_embed(self, texts: List[str]) -> List[List[float]]:
        import torch

        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            encoded = self._tokenizer(
                batch, padding=True, truncation=True,
                max_length=512, return_tensors="pt"
            ).to(self._device)

            with torch.no_grad():
                output = self._model(**encoded)

            # pooling
            if self.config.pooling == "cls":
                vectors = output.last_hidden_state[:, 0, :]
            elif self.config.pooling == "max":
                vectors = output.last_hidden_state.max(dim=1).values
            else:  # mean (default)
                attention_mask = encoded["attention_mask"].unsqueeze(-1).float()
                vectors = (output.last_hidden_state * attention_mask).sum(1) / attention_mask.sum(1)

            if self.config.normalize:
                vectors = torch.nn.functional.normalize(vectors, p=2, dim=-1)

            all_vectors.extend(vectors.cpu().tolist())

        return all_vectors

    # ── hosted inference API ──────────────────────────────────────────────────

    def _init_api(self, config: EmbeddingConfig):
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise ImportError(
                "huggingface_hub required → pip install huggingface-hub"
            ) from exc

        token = config.extra.get("api_key") or os.environ.get("HUGGINGFACE_API_KEY")
        from huggingface_hub import InferenceClient
        self._api_client = InferenceClient(model=config.model, token=token)

    def _api_embed(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            result = self._api_client.feature_extraction(batch)
            # result shape: (batch, seq_len, hidden) or (batch, hidden)
            import numpy as np
            arr = np.array(result)
            if arr.ndim == 3:
                arr = arr.mean(axis=1)   # mean pool
            all_vectors.extend(arr.tolist())
        return all_vectors

    # ── public interface ──────────────────────────────────────────────────────

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self._use_local:
            return self._local_embed(texts)
        return self._api_embed(texts)
