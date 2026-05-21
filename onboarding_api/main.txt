"""
main.py — ONBOARDING + INGESTION PIPELINE ONLY

This version removes ALL retrieval/query logic.

Responsibilities:
-----------------
1. Download source files
2. Extract text
3. Chunk documents
4. Generate embeddings
5. Build vector index

NO retrieval logic.
NO QueryFactory.
NO query execution.

This is correct architecture for onboarding_api service.
"""


import json
import os
import sys
from pathlib import Path
from typing import List

sys.stdout.reconfigure(encoding='utf-8')

import yaml
from dotenv import load_dotenv
from config.logger import setup_logger
from config.timer import log_execution_time

logger = setup_logger(__name__)

# ── Factory imports ────────────────────────────────────────────────────────────
from source.factory import DataSourceFactory
from chunking.factory import ChunkingFactory
from embedding.factory import EmbeddingFactory
from extractors.factory import ExtractorFactory
from vector_store.factory import VectorStoreFactory

# ── LlamaIndex ────────────────────────────────────────────────────────────────
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.core.base.embeddings.base import BaseEmbedding

from extractors.ocr_config import configure_tesseract

configure_tesseract()

# ── Environment setup ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent

ENV_CANDIDATES = [
    SCRIPT_DIR / ".env",
    SCRIPT_DIR.parent / ".env",
    SCRIPT_DIR.parent.parent / ".env",
]

for _env_path in ENV_CANDIDATES:
    if _env_path.exists():
        load_dotenv(_env_path)
        break
else:
    load_dotenv()

# ── Config loader ──────────────────────────────────────────────────────────────
@log_execution_time(logger)
def load_config(config_path: str) -> dict:
    """
    Load tenant-specific YAML configuration.
    """

    path = Path(config_path)

    if not path.exists():

        raise FileNotFoundError(
            f"Tenant config not found: {config_path}"
        )

    print("\n" + "=" * 60)
    print(f"[main] Loading tenant config:")
    print(config_path)
    print("=" * 60)

    with open(path, "r", encoding="utf-8") as f:

        return yaml.safe_load(f)
'''
def load_config() -> dict:
    """
    Load config.yaml
    """
    config_path = SCRIPT_DIR / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)'''

# ── Step 1: Download source files ─────────────────────────────────────────────

@log_execution_time(logger)
def download_source_files(config: dict) -> list[str]:
    """
    Download files from configured source.
    """

    source = DataSourceFactory.create(config)

    files = source.download()

    if not files:
        print("[main] No files downloaded from source.")

    return files

# ── Step 2: Extract documents ─────────────────────────────────────────────────

@log_execution_time(logger)
def extract_documents(file_paths: list[str], source_type: str) -> list[Document]:
    """
    Extract text from downloaded documents.
    """

    documents: list[Document] = []

    for file_path in file_paths:

        try:
            extractor = ExtractorFactory.get_extractor(file_path)

            text = extractor.extract_text(file_path)

            if not text or len(text.strip()) < 10:
                print(f"[main] Skipping empty document: {file_path}")
                continue

            print(f"\n--- EXTRACTED ({Path(file_path).name}) ---")
            print(text[:300])

            doc = Document(
                text=text,
                metadata={
                    "file_name": Path(file_path).name,
                    "file_path": file_path,
                    "source": source_type,
                },
            )

            documents.append(doc)

        except Exception as exc:
            print(f"[main] Error processing {file_path}: {exc}")

    return documents

# ── Step 3: Chunk documents ───────────────────────────────────────────────────

@log_execution_time(logger)
def chunk_documents(documents: list[Document], config: dict) -> list[BaseNode]:
    """
    Chunk documents using configured strategy.
    """

    chunker = ChunkingFactory.create(config)

    nodes = chunker.chunk(documents)

    print(f"\n[main] Total chunks created: {len(nodes)}")

    if nodes:
        first = nodes[0]

        print("\n--- SAMPLE CHUNK ---")

        try:
            print(json.dumps(first.to_dict(), indent=2)[:800])

        except Exception:
            print(first.text[:400] if hasattr(first, "text") else str(first)[:400])

    return nodes

# ── Embedder Adapter ───────────────────────────────────────────────────────────
class _BaseEmbedderAdapter(BaseEmbedding):
    """
    Adapter for custom embedders to work with LlamaIndex.
    """

    def __init__(self, embedder):
        super().__init__()
        self._embedder = embedder

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embedder.embed_query(text)

    def get_text_embedding_batch(
        self,
        texts: list[str],
        show_progress: bool = False
    ) -> list[list[float]]:
        return self._embedder.embed_texts(texts)

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embedder.embed_query(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embedder.embed_query(query)

    def get_agg_embedding_from_queries(self, queries, agg_fn=None):

        vecs = [self._get_query_embedding(q) for q in queries]

        if agg_fn:
            return agg_fn(vecs)

        if not vecs:
            return []

        dim = len(vecs[0])

        avg = [
            sum(v[i] for v in vecs) / len(vecs)
            for i in range(dim)
        ]

        return avg
# ── Step 4: Build vector index ────────────────────────────────────────────────

@log_execution_time(logger)
def build_vector_index(
    nodes: list[BaseNode],
    config: dict
) -> VectorStoreIndex:
    """
    Generate embeddings and create vector index.
    """

    embedding_provider = config["embedding"]["provider"].lower()

    # Validate OpenAI API key if needed
    if embedding_provider in ("openai", "azure_openai"):

        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            raise ValueError(
                "[main] OPENAI_API_KEY environment variable is not set."
            )

    # Create embedder
    embedder = EmbeddingFactory.create(config)

    print(f"[main] Embedder initialized: {embedder}")

    # OpenAI native embedder
    from llama_index.embeddings.openai import OpenAIEmbedding

    model_name = config["embedding"]["model"]

    if embedding_provider == "openai":

        llama_embed_model = OpenAIEmbedding(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=model_name,
        )

    else:
        llama_embed_model = _BaseEmbedderAdapter(embedder)

    # Create vector store
    vector_store = VectorStoreFactory.create(config)

    vector_store.connect()

    print(f"[main] Vector store connected: {vector_store}")

    # Create vector index
    index = VectorStoreIndex(
        nodes,
        embed_model=llama_embed_model,
        vector_store=vector_store,
    )

    print("[main] Vector index created successfully.")

    return index

# ── Pipeline orchestrator ─────────────────────────────────────────────────────

@log_execution_time(logger)
def run_pipeline(config: dict) -> VectorStoreIndex:
    """
    Full ingestion pipeline:
        1. Download
        2. Extract
        3. Chunk
        4. Embed
        5. Vector index
    """

    # Step 1
    print("\n" + "=" * 60)
    print("STEP 1: Downloading source files...")
    print(f"source.type = {config['source']['type']}")

    files = download_source_files(config)

    if not files:
        raise SystemExit("[main] No files downloaded.")

    # Step 2
    print("\n" + "=" * 60)
    print("STEP 2: Extracting documents...")

    documents = extract_documents(
        files,
        config["source"]["type"]
    )

    print(f"Valid documents: {len(documents)}")

    if not documents:
        raise SystemExit("[main] No valid documents extracted.")

    # Step 3
    print("\n" + "=" * 60)
    print("STEP 3: Chunking documents...")
    print(f"chunking.strategy = {config['chunking']['strategy']}")

    nodes = chunk_documents(documents, config)

    # Step 4
    print("\n" + "=" * 60)
    print("STEP 4: Building vector index...")
    print(f"embedding.provider = {config['embedding']['provider']}")

    index = build_vector_index(nodes, config)

    print("[main] Ingestion pipeline completed successfully.")

    return index

# ── Main entry point ──────────────────────────────────────────────────────────

@log_execution_time(logger)
def main():

    config = load_config("D:\OneDrive - REDINGTON\Work\Code\RAG\s1_rag_engine\onboarding_api\config.yaml")

    print("\n" + "=" * 60)
    print("ONBOARDING + INGESTION PIPELINE")
    print("=" * 60)

    print(f"source.type        = {config['source']['type']}")
    print(f"chunking.strategy  = {config['chunking']['strategy']}")
    print(f"embedding.provider = {config['embedding']['provider']}")

    # Run ingestion pipeline
    run_pipeline(config)

if __name__ == "__main__":
    main()