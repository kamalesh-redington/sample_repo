# config/config_loader.py

import os
import re
import yaml
from dataclasses import dataclass, field
from typing import List, Optional

def _interpolate_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with environment variable values."""
    return re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), m.group(0)), value)

def _resolve_env_vars(obj):
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(i) for i in obj]
    elif isinstance(obj, str):
        return _interpolate_env_vars(obj)
    return obj

@dataclass
class SourceConfig:
    type: str
    bucket: str
    prefix: str = ""
    region: str = "us-east-1"

@dataclass
class ChunkingConfig:
    chunk_size: int = 512
    chunk_overlap: int = 64
    split_by: str = "token"
    handle_images: bool = True

@dataclass
class EmbeddingConfig:
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 32

@dataclass
class VectorStoreConfig:
    type: str = "pgvector"
    host: str = "localhost"
    port: int = 5432
    database: str = "ragdb"
    user: str = "postgres"
    password: str = ""
    table: str = "document_chunks"
    index_type: str = "ivfflat"

@dataclass
class MetadataFieldConfig:
    name: str
    source: str

@dataclass
class MetadataConfig:
    fields: List[MetadataFieldConfig] = field(default_factory=list)
    tags: dict = field(default_factory=dict)

@dataclass
class IngestConfig:
    source: SourceConfig
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    vector_store: VectorStoreConfig
    metadata: MetadataConfig

    @classmethod
    def from_yaml(cls, path: str) -> "IngestConfig":
        with open(path) as f:
            raw = yaml.safe_load(f)
        raw = _resolve_env_vars(raw)

        meta_raw = raw.get("metadata", {})
        metadata = MetadataConfig(
            fields=[MetadataFieldConfig(**f) for f in meta_raw.get("fields", [])],
            tags=meta_raw.get("tags", {})
        )

        return cls(
            source=SourceConfig(**raw["source"]),
            chunking=ChunkingConfig(**raw.get("chunking", {})),
            embedding=EmbeddingConfig(**raw.get("embedding", {})),
            vector_store=VectorStoreConfig(**raw.get("vector_store", {})),
            metadata=metadata
        )
