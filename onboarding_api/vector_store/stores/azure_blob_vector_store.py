"""
Azure Blob Vector Store  (Azure Blob Storage + in-memory FAISS)
Type key : "azure_blob_vector"

Same hybrid pattern as S3VectorStore, backed by Azure Blob Storage.

Extra config fields (from object_store section):
    connection_string : (or env AZURE_STORAGE_CONNECTION_STRING)
    account_name      : storage account
    account_key       : (or env AZURE_STORAGE_KEY)
    container         : blob container name  (maps to bucket)
    prefix            : "embeddings/"
    storage_format    : "parquet"
"""

import io
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from vector_store.base import (
    BaseVectorStore, ObjectStoreConfig, QueryResult, VectorDocument, VectorStoreConfig,
)


class AzureBlobVectorStore(BaseVectorStore):
    """Hybrid Azure Blob Storage + FAISS vector store."""

    def __init__(self, config: VectorStoreConfig, object_config: Optional[ObjectStoreConfig] = None):
        super().__init__(config)
        self._obj_cfg   = object_config or ObjectStoreConfig(provider="azure")
        self._client    = None
        self._container = None
        self._index     = None
        self._ids:       List[str]            = []
        self._texts:     List[str]            = []
        self._metadata:  List[Dict[str, Any]] = []
        self._vectors:   List[List[float]]    = []
        self._dim        = config.extra.get("dimensions", 1536)

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:
            raise ImportError(
                "azure-storage-blob required → pip install azure-storage-blob"
            ) from exc

        from azure.storage.blob import BlobServiceClient

        conn_str = (
            self._obj_cfg.extra.get("connection_string")
            or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        )
        if conn_str:
            svc = BlobServiceClient.from_connection_string(conn_str)
        else:
            account = self._obj_cfg.extra.get("account_name", "")
            key     = self._obj_cfg.extra.get("account_key") or os.environ.get("AZURE_STORAGE_KEY", "")
            svc     = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=key,
            )

        container_name = self._obj_cfg.extra.get("container", self._obj_cfg.bucket)
        self._container = svc.get_container_client(container_name)
        try:
            self._container.create_container()
        except Exception:
            pass   # already exists

        self._rebuild_index_from_azure()

    def close(self) -> None:
        pass

    # ── Azure helpers ─────────────────────────────────────────────────────────

    def _blob_name(self, path_type: str, name: str) -> str:
        sub = getattr(self._obj_cfg, f"{path_type}_path", f"{path_type}/")
        return f"{self._obj_cfg.prefix.rstrip('/')}/{sub.strip('/')}/{name}"

    def _put_parquet(self, data: List[Dict], path_type: str, name: str) -> None:
        import pandas as pd

        buf = io.BytesIO()
        pd.DataFrame(data).to_parquet(buf, index=False)
        buf.seek(0)
        blob_client = self._container.get_blob_client(self._blob_name(path_type, name))
        blob_client.upload_blob(buf, overwrite=True)

    def _rebuild_index_from_azure(self) -> None:
        try:
            import faiss, numpy as np
        except ImportError as exc:
            raise ImportError("faiss-cpu + numpy required → pip install faiss-cpu numpy") from exc

        self._faiss  = faiss
        metric       = self.config.index.metric
        self._index  = faiss.IndexFlatIP(self._dim) if metric in ("cosine", "dot_product") \
                       else faiss.IndexFlatL2(self._dim)

        prefix  = self._blob_name("embeddings", "")
        blobs   = self._container.list_blobs(name_starts_with=prefix)

        for blob in blobs:
            if not blob.name.endswith(".parquet"):
                continue
            import pandas as pd
            data = self._container.get_blob_client(blob.name).download_blob().readall()
            df   = pd.read_parquet(io.BytesIO(data))
            for _, row in df.iterrows():
                vec = json.loads(row["vector"]) if isinstance(row["vector"], str) else row["vector"]
                self._ids.append(row["id"])
                self._texts.append(row.get("text", ""))
                self._metadata.append(
                    json.loads(row.get("metadata", "{}"))
                    if isinstance(row.get("metadata"), str) else row.get("metadata", {})
                )
                self._vectors.append(vec)

        if self._vectors:
            self._index.add(np.array(self._vectors, dtype="float32"))

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        import numpy as np

        batch_id = str(uuid.uuid4())[:8]
        rows = []
        for doc in documents:
            rows.append({"id": doc.id, "vector": str(doc.vector),
                         "text": doc.text, "metadata": json.dumps(doc.metadata)})
            self._ids.append(doc.id)
            self._texts.append(doc.text)
            self._metadata.append(doc.metadata)
            self._vectors.append(doc.vector)

        self._index.add(np.array([d.vector for d in documents], dtype="float32"))
        self._put_parquet(rows, "embeddings", f"{batch_id}.parquet")

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        import numpy as np

        k              = top_k or self.config.query_top_k
        scores, indices = self._index.search(np.array([vector], dtype="float32"), k)
        results         = []
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
