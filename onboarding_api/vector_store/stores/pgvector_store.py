"""
PGVector Store
Type key : "pgvector"
Backend  : PostgreSQL + pgvector extension

Supported index types:
    ivfflat  → fast approximate (classic)
    hnsw     → better recall, lower latency (pgvector ≥ 0.5)

Supported metrics:
    cosine      → <=>
    l2          → <->
    dot_product → <#>

Extra config fields:
    ssl_mode : "require" | "disable" | "prefer"
    schema   : "public"
"""

import uuid
from typing import Any, Dict, List, Optional

from vector_store.base import BaseVectorStore, QueryResult, VectorDocument, VectorStoreConfig

# Operator map: metric → pgvector SQL operator
_METRIC_OPS = {
    "cosine":      "<=>",
    "l2":          "<->",
    "dot_product": "<#>",
}


class PGVectorStore(BaseVectorStore):
    """PostgreSQL pgvector adapter."""

    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self._conn = None
        self._op = _METRIC_OPS.get(config.index.metric, "<=>")

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            import psycopg2
        except ImportError as exc:
            raise ImportError("psycopg2 required → pip install psycopg2-binary") from exc

        import psycopg2
        self._conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.database,
            user=self.config.user,
            password=self.config.password,
            sslmode=self.config.extra.get("ssl_mode", "prefer"),
        )
        self._ensure_table()
        self._ensure_index()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── schema helpers ────────────────────────────────────────────────────────

    def _table(self) -> str:
        return f"{self.config.schema}.{self.config.collection_name}"

    def _ensure_table(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table()} (
                    id          TEXT PRIMARY KEY,
                    embedding   VECTOR,
                    text        TEXT,
                    metadata    JSONB DEFAULT '{{}}'::jsonb,
                    inserted_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
        self._conn.commit()

    def _ensure_index(self) -> None:
        idx_type = self.config.index.type.lower()
        params   = self.config.index.params
        col      = self.config.collection_name

        with self._conn.cursor() as cur:
            if idx_type == "hnsw":
                m    = params.get("m", 16)
                ef   = params.get("ef_construction", 200)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {col}_hnsw_idx
                    ON {self._table()} USING hnsw (embedding vector_cosine_ops)
                    WITH (m = {m}, ef_construction = {ef});
                """)
            else:   # ivfflat (default)
                lists = params.get("lists", 100)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {col}_ivf_idx
                    ON {self._table()} USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {lists});
                """)
        self._conn.commit()

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(self, documents: List[VectorDocument]) -> None:
        import json as _json

        sql = f"""
            INSERT INTO {self._table()} (id, embedding, text, metadata)
            VALUES (%s, %s::vector, %s, %s)
            ON CONFLICT (id) DO UPDATE
                SET embedding   = EXCLUDED.embedding,
                    text        = EXCLUDED.text,
                    metadata    = EXCLUDED.metadata,
                    inserted_at = NOW();
        """
        with self._conn.cursor() as cur:
            for i in range(0, len(documents), self.config.insert_batch_size):
                batch = documents[i : i + self.config.insert_batch_size]
                rows = [
                    (
                        doc.id,
                        str(doc.vector),           # pgvector expects '[f,f,f]' string
                        doc.text,
                        _json.dumps(doc.metadata),
                    )
                    for doc in batch
                ]
                cur.executemany(sql, rows)
        self._conn.commit()

    # ── read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[QueryResult]:
        import json as _json

        k        = top_k or self.config.query_top_k
        vec_str  = str(vector)
        where    = ""

        if filters:
            clauses = [
                f"metadata->>{_json.dumps(k)} = {_json.dumps(str(v))}"
                for k, v in filters.items()
            ]
            where = "WHERE " + " AND ".join(clauses)

        sql = f"""
            SELECT id, text, metadata,
                   1 - (embedding {self._op} %s::vector) AS score
            FROM   {self._table()}
            {where}
            ORDER  BY embedding {self._op} %s::vector
            LIMIT  %s;
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, (vec_str, vec_str, k))
            rows = cur.fetchall()

        return [
            QueryResult(
                id=row[0],
                text=row[1],
                metadata=row[2] if isinstance(row[2], dict) else _json.loads(row[2] or "{}"),
                score=float(row[3]),
            )
            for row in rows
        ]

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, ids: List[str]) -> None:
        sql = f"DELETE FROM {self._table()} WHERE id = ANY(%s);"
        with self._conn.cursor() as cur:
            cur.execute(sql, (ids,))
        self._conn.commit()
