"""
BM25 Sparse Embedder
Provider key  : "bm25"
Embedding type: sparse
Modality      : text

Classic lexical sparse retrieval — fast, no GPU needed.

Extra config fields:
    k1          : 1.5   (term saturation)
    b           : 0.75  (length normalization)
    corpus      : list of docs to fit BM25 on (optional; fit on first batch otherwise)
    language    : "english"  (stemmer language for preprocessing)
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class BM25Embedder(BaseEmbedder):
    """
    BM25 sparse embedder backed by rank_bm25.

    Unlike neural models, BM25 builds a vocabulary from a corpus first.
    Call fit(corpus) before embed_texts() if not supplying corpus in config.
    """

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:
            raise ImportError(
                "rank-bm25 required → pip install rank-bm25"
            ) from exc

        from rank_bm25 import BM25Okapi
        self._BM25Okapi = BM25Okapi
        self._k1: float = config.extra.get("k1", 1.5)
        self._b: float = config.extra.get("b", 0.75)
        self._bm25 = None
        self._vocab: List[str] = []

        corpus = config.extra.get("corpus")
        if corpus:
            self.fit(corpus)

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def fit(self, corpus: List[str]) -> "BM25Embedder":
        """Fit BM25 index on a list of documents."""
        tokenized = [self._tokenize(doc) for doc in corpus]
        self._bm25 = self._BM25Okapi(tokenized, k1=self._k1, b=self._b)
        # Collect vocabulary
        vocab_set = set()
        for tokens in tokenized:
            vocab_set.update(tokens)
        self._vocab = sorted(vocab_set)
        return self

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Return BM25 score vectors aligned to the fitted vocabulary.
        Requires fit() to have been called first.
        """
        if self._bm25 is None:
            # Auto-fit on the provided texts
            self.fit(texts)

        all_vectors: List[List[float]] = []
        for text in texts:
            query_tokens = self._tokenize(text)
            scores = self._bm25.get_scores(query_tokens)  # numpy array
            all_vectors.append(scores.tolist())

        return all_vectors
