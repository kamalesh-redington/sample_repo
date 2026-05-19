"""
ColBERT Late-Interaction Embedder
Provider key  : "colbert"
Embedding type: late_interaction
Modality      : text

Stores per-token embeddings instead of one pooled vector.
Scoring uses MaxSim (max inner-product per query token over doc tokens).

Models:
    - colbert-ir/colbertv2.0     (128-dim per token, default)
    - answerdotai/answerai-colbert-small-v1

Extra config fields:
    device     : "cpu" | "cuda"
    max_length : 512
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class ColBERTEmbedder(BaseEmbedder):
    """
    Late-interaction token-level embedder.

    embed_texts() returns a FLAT list of Lists where each element is
    a list of token vectors (shape: [seq_len, dim]) serialized as a
    flat 1-D float array.  Use embed_tokens() to get the structured output.
    """

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "transformers + torch required → pip install transformers torch"
            ) from exc

        import torch
        from transformers import AutoModel, AutoTokenizer

        self._device = torch.device(config.extra.get("device", "cpu"))
        self._max_length: int = config.extra.get("max_length", 512)
        self._tokenizer = AutoTokenizer.from_pretrained(config.model)
        self._model = AutoModel.from_pretrained(config.model).to(self._device)
        self._model.eval()
        self._torch = torch

    def embed_tokens(self, texts: List[str]) -> List[List[List[float]]]:
        """
        Returns per-document token-level embeddings.

        Shape: List[doc] → List[token] → List[float(dim)]
        """
        import torch

        all_token_vecs: List[List[List[float]]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            ).to(self._device)

            with torch.no_grad():
                output = self._model(**encoded)

            token_embeddings = output.last_hidden_state  # (B, T, D)

            if self.config.normalize:
                token_embeddings = torch.nn.functional.normalize(
                    token_embeddings, p=2, dim=-1
                )

            # Unpad: keep only non-padding tokens per doc
            attention_mask = encoded["attention_mask"]  # (B, T)
            for doc_idx in range(len(batch)):
                lengths = attention_mask[doc_idx].sum().item()
                vecs = token_embeddings[doc_idx, :int(lengths), :]
                all_token_vecs.append(vecs.cpu().tolist())

        return all_token_vecs

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Compatibility shim: returns mean-pooled CLS-equivalent vector.
        Use embed_tokens() for full late-interaction retrieval.
        """
        import torch

        token_vecs_list = self.embed_tokens(texts)
        result: List[List[float]] = []
        for token_vecs in token_vecs_list:
            arr = torch.tensor(token_vecs).mean(dim=0)
            result.append(arr.tolist())
        return result
