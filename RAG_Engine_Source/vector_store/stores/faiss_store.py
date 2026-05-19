"""
FAISS Local Vector Store
Type key : "faiss"
Backend  : Meta FAISS (in-memory or on-disk index)

Supports:
    - IndexFlatL2 / IndexFlatIP (exact search)
    - IndexIVFFlat (approximate)
    - IndexHNSWFlat (graph-based, best quality)

Extra config fields:
    index_path : "./faiss.index"   (path to persist/load index)
    id_map_path: "./faiss_ids.json" (parallel ID mapping file)
    nlist      : 100               (IVF number of clusters)
    nprobe     : 10                (IVF search probes)
    device     : "cpu"             ("gpu" requires faiss-gpu)
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig


class FAISSStore(BaseVectorStore):
    """
    In-process FAISS vector store with optional on-disk persistence.

    ID mapping: FAISS only stores integer indices.
    We maintain a parallel list self._ids (str) and self._texts / self._metadata
    aligned with FAISS internal positions.
    """

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._index    = None
        self._ids:      List[str]             = []
        self._texts:    List[str]             = []
        self._metadata: List[Dict[str, Any]]  = []

        self._index_path   = Path(config.extra.get("index_path",    "./faiss.index"))
        self._id_map_path  = Path(config.extra.get("id_map_path",   "./faiss_ids.json"))
        self._dim          = config.extra.get("dimensions", 1536)

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss-cpu required → pip install faiss-cpu") from exc

        import faiss as _faiss
        self._faiss = _faiss

        idx_type = self.config.index.type.lower()
        metric   = self.config.index.metric

        if self._index_path.exists() and self._id_map_path.exists():
            self._index = _faiss.read_index(str(self._index_path))
            with open(self._id_map_path, "r") as f:
                stored = json.load(f)
            self._ids      = stored.get("ids", [])
            self._texts    = stored.get("texts", [])
            self._metadata = stored.get("metadata", [])
        else:
            self._index = self._build_index(idx_type, metric, _faiss)

    def _build_index(self, idx_type: str, metric: str, faiss):
        inner_product = metric in ("cosine", "dot_product")
        base = faiss.IndexFlatIP(self._dim) if inner_product else faiss.IndexFlatL2(self._dim)

        if idx_type in ("ivf", "ivfflat"):
            nlist = self.config.extra.get("nlist", 100)
            index = faiss.IndexIVFFlat(base, self._dim, nlist)
        elif idx_type == "hnsw":
            m     = self.config.index.params.get("m", 32)
            index = faiss.IndexHNSWFlat(self._dim, m)
            index.hnsw.efConstruction = self.config.index.params.get("ef_construction", 200)
        else:
            index = base  # flat exact search

        return index

    def close(self) -> None:
        self._persist()

    def _persist(self) -> None:
        if self._index is not None:
            self._faiss.write_index(self._index, str(self._index_path))
            with open(self._id_map_path, "w") as f:
                json.dump({
                    "ids":      self._ids,
                    "texts":    self._texts,
                    "metadata": self._metadata,
                }, f)

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        import numpy as np

        new_vecs = np.array([d.vector for d in documents], dtype="float32")

        if not self._index.is_trained:
            self._index.train(new_vecs)

        self._index.add(new_vecs)
        self._ids.extend(d.id for d in documents)
        self._texts.extend(d.text for d in documents)
        self._metadata.extend(d.metadata for d in documents)

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        import numpy as np

        k = top_k or self.config.query_top_k
        if hasattr(self._index, "hnsw"):
            self._index.hnsw.efSearch = self.config.index.params.get("ef_search", 64)
        if hasattr(self._index, "nprobe"):
            self._index.nprobe = self.config.extra.get("nprobe", 10)

        query_arr = np.array([vector], dtype="float32")
        scores, indices = self._index.search(query_arr, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self._ids):
                continue
            meta = self._metadata[idx]
            # post-filter (FAISS has no native metadata filter)
            if filters and not all(meta.get(fk) == fv for fk, fv in filters.items()):
                continue
            results.append(QueryResult(
                id=self._ids[idx],
                score=float(score),
                text=self._texts[idx],
                metadata=meta,
            ))
        return results

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        """FAISS does not support removal. We rebuild without the deleted IDs."""
        import numpy as np

        keep_mask = [i for i, sid in enumerate(self._ids) if sid not in set(ids)]
        if not keep_mask:
            self._ids, self._texts, self._metadata = [], [], []
            self._index = self._build_index(
                self.config.index.type, self.config.index.metric, self._faiss
            )
            return

        all_vecs = self._faiss.rev_swig_ptr(self._index.get_xb(), self._index.ntotal * self._dim)
        all_vecs = np.array(all_vecs).reshape(self._index.ntotal, self._dim)
        kept_vecs = all_vecs[keep_mask]

        self._ids      = [self._ids[i]      for i in keep_mask]
        self._texts    = [self._texts[i]    for i in keep_mask]
        self._metadata = [self._metadata[i] for i in keep_mask]

        self._index = self._build_index(
            self.config.index.type, self.config.index.metric, self._faiss
        )
        self.upsert([
            VectorDocument(id=self._ids[i], vector=kept_vecs[i].tolist(),
                           text=self._texts[i], metadata=self._metadata[i])
            for i in range(len(self._ids))
        ])
