"""
GCS Vector Store  (Google Cloud Storage + in-memory FAISS)
Type key : "gcs_vector"

Same hybrid pattern as S3VectorStore, backed by GCS.

Extra config fields (from object_store section):
    bucket          : "my-rag-bucket"
    prefix          : "embeddings/"
    project         : GCP project ID
    credentials_file: path to service account JSON (or env GOOGLE_APPLICATION_CREDENTIALS)
    storage_format  : "parquet"
"""

import io
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore, ObjectStoreConfig, QueryResult, VectorDocument, VectorStoreConfig,
)


class GCSVectorStore(BaseVectorStore):
    """Hybrid GCS + FAISS vector store."""

    def __init__(self, config: VectorStoreConfig, object_config: Optional[ObjectStoreConfig] = None):
        super().__init__(config)
        self._obj_cfg   = object_config or ObjectStoreConfig(provider="gcs")
        self._client    = None
        self._bucket    = None
        self._index     = None
        self._ids:       List[str]            = []
        self._texts:     List[str]            = []
        self._metadata:  List[Dict[str, Any]] = []
        self._vectors:   List[List[float]]    = []
        self._dim        = config.extra.get("dimensions", 1536)

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise ImportError(
                "google-cloud-storage required → pip install google-cloud-storage"
            ) from exc

        from google.cloud import storage as gcs

        creds_file = self._obj_cfg.extra.get("credentials_file") or \
                     os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_file:
            self._client = gcs.Client.from_service_account_json(
                creds_file, project=self._obj_cfg.extra.get("project")
            )
        else:
            self._client = gcs.Client(project=self._obj_cfg.extra.get("project"))

        self._bucket = self._client.bucket(self._obj_cfg.bucket)
        self._rebuild_index_from_gcs()

    def close(self) -> None:
        pass   # GCS client doesn't need explicit close

    # ── GCS helpers ───────────────────────────────────────────────────────────

    def _blob_name(self, path_type: str, name: str) -> str:
        path_attr = f"{path_type}_path"
        sub       = getattr(self._obj_cfg, path_attr, f"{path_type}/")
        return f"{self._obj_cfg.prefix.rstrip('/')}/{sub.strip('/')}/{name}"

    def _put_parquet(self, data: List[Dict], path_type: str, name: str) -> None:
        import pandas as pd

        buf = io.BytesIO()
        pd.DataFrame(data).to_parquet(buf, index=False)
        buf.seek(0)
        blob = self._bucket.blob(self._blob_name(path_type, name))
        blob.upload_from_file(buf, content_type="application/octet-stream")

    def _rebuild_index_from_gcs(self) -> None:
        try:
            import faiss, numpy as np
        except ImportError as exc:
            raise ImportError("faiss-cpu + numpy required → pip install faiss-cpu numpy") from exc

        self._faiss = faiss
        metric      = self.config.index.metric
        self._index = faiss.IndexFlatIP(self._dim) if metric in ("cosine", "dot_product") \
                      else faiss.IndexFlatL2(self._dim)

        prefix = self._blob_name("embeddings", "")
        blobs  = list(self._client.list_blobs(self._obj_cfg.bucket, prefix=prefix))

        for blob in blobs:
            if not blob.name.endswith(".parquet"):
                continue
            import pandas as pd
            buf  = io.BytesIO(blob.download_as_bytes())
            df   = pd.read_parquet(buf)
            for _, row in df.iterrows():
                vec = json.loads(row["vector"]) if isinstance(row["vector"], str) else row["vector"]
                self._ids.append(row["id"])
                self._texts.append(row.get("text", ""))
                self._metadata.append(
                    json.loads(row["metadata"]) if isinstance(row.get("metadata", "{}"), str)
                    else row.get("metadata", {})
                )
                self._vectors.append(vec)

        if self._vectors:
            self._index.add(np.array(self._vectors, dtype="float32"))

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        import numpy as np

        batch_id = str(uuid.uuid4())[:8]
        emb_rows = []
        for doc in documents:
            emb_rows.append({"id": doc.id, "vector": str(doc.vector),
                             "text": doc.text, "metadata": json.dumps(doc.metadata)})
            self._ids.append(doc.id)
            self._texts.append(doc.text)
            self._metadata.append(doc.metadata)
            self._vectors.append(doc.vector)

        self._index.add(np.array([d.vector for d in documents], dtype="float32"))
        self._put_parquet(emb_rows, "embeddings", f"{batch_id}.parquet")

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        import numpy as np

        k         = top_k or self.config.query_top_k
        scores, indices = self._index.search(np.array([vector], dtype="float32"), k)
        results   = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self._ids):
                continue
            meta = self._metadata[idx]
            if filters and not all(meta.get(fk) == fv for fk, fv in filters.items()):
                continue
            results.append(QueryResult(id=self._ids[idx], score=float(score),
                                       text=self._texts[idx], metadata=meta))
        return results

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        del_set        = set(ids)
        keep           = [i for i, sid in enumerate(self._ids) if sid not in del_set]
        self._ids      = [self._ids[i]      for i in keep]
        self._texts    = [self._texts[i]    for i in keep]
        self._metadata = [self._metadata[i] for i in keep]
        self._vectors  = [self._vectors[i]  for i in keep]
        import numpy as np, faiss
        self._index = faiss.IndexFlatIP(self._dim) if self.config.index.metric in ("cosine", "dot_product") \
                      else faiss.IndexFlatL2(self._dim)
        if self._vectors:
            self._index.add(np.array(self._vectors, dtype="float32"))
