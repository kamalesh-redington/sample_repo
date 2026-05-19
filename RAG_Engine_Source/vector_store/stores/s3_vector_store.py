"""
S3 Vector Store  (Hybrid: embeddings in S3 as Parquet + FAISS index in memory)
Type key : "s3_vector"

Architecture:
    ┌──────────────┐        ┌──────────────────────────────────┐
    │  upsert()    │──────▶ │  S3 bucket                       │
    │              │        │   embeddings/{batch_id}.parquet   │
    │              │        │   documents/{batch_id}.parquet    │
    │              │        │   metadata/{batch_id}.parquet     │
    └──────────────┘        └──────────────────────────────────┘
                                         │
    ┌──────────────┐                     ▼
    │  query()     │◀──── FAISS in-memory index (rebuilt from S3 on connect)
    └──────────────┘

Extra config fields (read from object_store section):
    bucket          : "my-rag-bucket"
    region          : "us-east-1"
    prefix          : "embeddings/"
    access_key      : (or env AWS_ACCESS_KEY_ID)
    secret_key      : (or env AWS_SECRET_ACCESS_KEY)
    storage_format  : "parquet"          (parquet | npy)
    sync_on_close   : true              (persist index back to S3 on close)
"""

import io
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore, ObjectStoreConfig, QueryResult, VectorDocument, VectorStoreConfig,
)


class S3VectorStore(BaseVectorStore):
    """
    Hybrid vector store: raw data (embeddings + docs + metadata) in S3,
    FAISS in-memory index for fast similarity search.
    """

    def __init__(self, config: VectorStoreConfig, object_config: Optional[ObjectStoreConfig] = None):
        super().__init__(config)
        self._obj_cfg = object_config or ObjectStoreConfig()
        self._s3      = None
        self._index   = None
        self._ids:      List[str]            = []
        self._texts:    List[str]            = []
        self._metadata: List[Dict[str, Any]] = []
        self._vectors:  List[List[float]]    = []
        self._dim       = config.extra.get("dimensions", 1536)

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        import boto3

        self._s3 = boto3.client(
            "s3",
            region_name=self._obj_cfg.region,
            aws_access_key_id=self._obj_cfg.access_key or os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=self._obj_cfg.secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        self._rebuild_index_from_s3()

    def close(self) -> None:
        if self.config.extra.get("sync_on_close", True):
            self._sync_faiss_to_s3()

    # ── S3 helpers ────────────────────────────────────────────────────────────

    def _s3_key(self, path_type: str, name: str) -> str:
        prefix = getattr(self._obj_cfg, f"{path_type}_path", f"{path_type}/")
        return f"{self._obj_cfg.prefix.rstrip('/')}/{prefix.strip('/')}/{name}"

    def _put_parquet(self, data: List[Dict], path_type: str, name: str) -> None:
        import pandas as pd

        buf = io.BytesIO()
        pd.DataFrame(data).to_parquet(buf, index=False)
        buf.seek(0)
        self._s3.put_object(
            Bucket=self._obj_cfg.bucket,
            Key=self._s3_key(path_type, name),
            Body=buf.getvalue(),
        )

    def _list_parquet_keys(self, path_type: str) -> List[str]:
        prefix = self._s3_key(path_type, "")
        resp   = self._s3.list_objects_v2(Bucket=self._obj_cfg.bucket, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", []) if obj["Key"].endswith(".parquet")]

    def _read_parquet(self, key: str):
        import pandas as pd

        obj  = self._s3.get_object(Bucket=self._obj_cfg.bucket, Key=key)
        data = obj["Body"].read()
        return pd.read_parquet(io.BytesIO(data))

    def _rebuild_index_from_s3(self) -> None:
        """Load all stored embeddings from S3 and rebuild FAISS in memory."""
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise ImportError("faiss-cpu + numpy required → pip install faiss-cpu numpy") from exc

        self._faiss = faiss

        metric   = self.config.index.metric
        base_idx = faiss.IndexFlatIP(self._dim) if metric in ("cosine", "dot_product") \
                   else faiss.IndexFlatL2(self._dim)
        self._index = base_idx

        try:
            emb_keys = self._list_parquet_keys("embeddings")
        except Exception:
            return     # bucket / prefix doesn't exist yet — start fresh

        for key in emb_keys:
            df = self._read_parquet(key)
            for _, row in df.iterrows():
                vec = json.loads(row["vector"]) if isinstance(row["vector"], str) else row["vector"]
                self._ids.append(row["id"])
                self._texts.append(row.get("text", ""))
                self._metadata.append(json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row.get("metadata", {}))
                self._vectors.append(vec)

        if self._vectors:
            self._index.add(np.array(self._vectors, dtype="float32"))

    def _sync_faiss_to_s3(self) -> None:
        """Write the current FAISS index binary to S3."""
        if self._index is None or self._index.ntotal == 0:
            return
        import faiss

        buf = io.BytesIO()
        faiss.write_index(self._index, faiss.PyCallbackIOWriter(buf.write))
        self._s3.put_object(
            Bucket=self._obj_cfg.bucket,
            Key=self._s3_key("embeddings", "faiss.index"),
            Body=buf.getvalue(),
        )

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        import json as _json
        import numpy as np

        batch_id = str(uuid.uuid4())[:8]
        emb_rows, doc_rows, meta_rows = [], [], []

        vecs = []
        for doc in documents:
            emb_rows.append({"id": doc.id, "vector": str(doc.vector), "text": doc.text})
            doc_rows.append({"id": doc.id, "text": doc.text})
            meta_rows.append({"id": doc.id, "metadata": _json.dumps(doc.metadata)})
            self._ids.append(doc.id)
            self._texts.append(doc.text)
            self._metadata.append(doc.metadata)
            vecs.append(doc.vector)

        self._index.add(np.array(vecs, dtype="float32"))
        self._vectors.extend(vecs)

        # Persist to S3
        self._put_parquet(emb_rows,  "embeddings", f"{batch_id}.parquet")
        self._put_parquet(doc_rows,  "documents",  f"{batch_id}.parquet")
        self._put_parquet(meta_rows, "metadata",   f"{batch_id}.parquet")

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        import numpy as np

        k = top_k or self.config.query_top_k
        query_arr = np.array([vector], dtype="float32")
        scores, indices = self._index.search(query_arr, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self._ids):
                continue
            meta = self._metadata[idx]
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
        """S3 objects are immutable batches; mark deleted in-memory and rebuild."""
        del_set       = set(ids)
        self._ids      = [i for i in self._ids if i not in del_set]
        self._texts    = [t for i, t in zip(self._ids, self._texts)]
        self._metadata = [m for i, m in zip(self._ids, self._metadata)]
        self._vectors  = [v for i, v in zip(self._ids, self._vectors)]
        # Rebuild FAISS
        import numpy as np, faiss
        base = faiss.IndexFlatIP(self._dim) if self.config.index.metric in ("cosine", "dot_product") \
               else faiss.IndexFlatL2(self._dim)
        self._index = base
        if self._vectors:
            self._index.add(np.array(self._vectors, dtype="float32"))
