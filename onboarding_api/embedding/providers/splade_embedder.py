"""
SPLADE Sparse Embedder
Provider key : "splade"
Embedding type: sparse
Modality     : text

Produces a sparse vocabulary-sized vector (BERT vocab ~30k terms).

Models:
    - naver/splade-cocondenser-ensembledistil  (strong, default)
    - naver/splade-v3
    - naver/splade-cocondenser-selfdistil      (smaller/faster)

Extra config fields:
    device     : "cpu" | "cuda"
    topk       : keep only top-k non-zero terms (default: 256, 0=keep all)
"""

from typing import Dict, List, Tuple

from embedding.base import BaseEmbedder, EmbeddingConfig


class SpladeEmbedder(BaseEmbedder):
    """
    Neural sparse embedder using SPLADE.

    embed_texts() returns dense float arrays shaped like the BERT vocab
    (length ≈ 30522) but with many near-zero values.

    For actual sparse storage (e.g., Pinecone sparse vectors), call
    to_sparse_dict() to get {token_id: weight} dicts instead.
    """

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import torch
            from transformers import AutoModelForMaskedLM, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "transformers + torch required → pip install transformers torch"
            ) from exc

        import torch
        from transformers import AutoModelForMaskedLM, AutoTokenizer

        self._device = torch.device(config.extra.get("device", "cpu"))
        self._tokenizer = AutoTokenizer.from_pretrained(config.model)
        self._model = AutoModelForMaskedLM.from_pretrained(config.model).to(self._device)
        self._model.eval()
        self._topk: int = config.extra.get("topk", 256)
        self._torch = torch

    def _to_splade_vector(self, logits) -> "torch.Tensor":
        """Apply log-saturation pooling: log(1 + relu(logits)).max(dim=1)."""
        return self._torch.log(1 + self._torch.relu(logits)).max(dim=1).values

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Returns dense-form sparse vectors (vocab-length float arrays)."""
        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            encoded = self._tokenizer(
                batch, padding=True, truncation=True,
                max_length=512, return_tensors="pt"
            ).to(self._device)

            with self._torch.no_grad():
                output = self._model(**encoded)

            sparse_vecs = self._to_splade_vector(output.logits)  # (batch, vocab)

            if self._topk > 0:
                # Zero-out all but top-k non-negative activations
                topk_vals, topk_idx = self._torch.topk(sparse_vecs, self._topk, dim=-1)
                mask = self._torch.zeros_like(sparse_vecs)
                mask.scatter_(1, topk_idx, topk_vals)
                sparse_vecs = mask

            all_vectors.extend(sparse_vecs.cpu().tolist())

        return all_vectors

    def to_sparse_dicts(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        Return sparse {token_id: weight} dicts — suitable for Pinecone
        sparse vectors, Weaviate sparse fields, etc.
        """
        dense_vecs = self.embed_texts(texts)
        result: List[Dict[int, float]] = []
        for vec in dense_vecs:
            result.append(
                {idx: val for idx, val in enumerate(vec) if val > 0}
            )
        return result
