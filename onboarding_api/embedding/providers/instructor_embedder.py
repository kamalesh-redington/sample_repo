"""
Instructor Embedder (Instruction-Tuned Dense Embedder)
Provider key : "instructor"
Embedding type: instructor
Modality     : text

Models:
    - hkunlp/instructor-xl        (768-dim, strongest)
    - hkunlp/instructor-large     (768-dim)
    - hkunlp/instructor-base      (768-dim, lightweight)

Instruction examples:
    "Represent the scientific document for retrieval:"
    "Represent the query for semantic search:"

Extra config fields:
    device     : "cpu" | "cuda" | "mps"
    instruction: override config.instruction at runtime
"""

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class InstructorEmbedder(BaseEmbedder):
    """
    Instruction-tuned dense embedder.
    Every text is prefixed with an instruction string that
    conditions the embedding's meaning (retrieval, clustering, etc.).
    """

    _DEFAULT_INSTRUCTION = "Represent the document for retrieval:"

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from InstructorEmbedding import INSTRUCTOR
        except ImportError as exc:
            raise ImportError(
                "InstructorEmbedding required → pip install InstructorEmbedding"
            ) from exc

        from InstructorEmbedding import INSTRUCTOR
        self._model = INSTRUCTOR(
            config.model,
            device=config.extra.get("device", "cpu"),
        )
        self._instruction = (
            config.instruction
            or config.extra.get("instruction")
            or self._DEFAULT_INSTRUCTION
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Instructor expects [[instruction, text], ...]
        pairs = [[self._instruction, t] for t in texts]
        vectors = self._model.encode(
            pairs,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize,
            show_progress_bar=False,
        )
        return vectors.tolist()
