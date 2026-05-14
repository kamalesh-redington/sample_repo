"""
main.py — RAG Engine II pipeline entry point.

Everything is loaded **dynamically from config.yaml** through three factories:

  ┌──────────────────────┬──────────────────────────┬──────────────────────────┐
  │ Step                 │ Factory                  │ Config key               │
  ├──────────────────────┼──────────────────────────┼──────────────────────────┤
  │ 1. Fetch documents   │ DataSourceFactory.create │ source.type              │
  │ 2. Extract text      │ ExtractorFactory         │ (file extension-based)   │
  │ 3. Chunk documents   │ ChunkingFactory.create   │ chunking.strategy        │
  │ 4. Embed & index     │ EmbeddingFactory.create  │ embedding.provider       │
  └──────────────────────┴──────────────────────────┴──────────────────────────┘

To switch any provider, edit the corresponding key in config.yaml — no code
changes are required.
"""

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import faiss
import yaml
from dotenv import load_dotenv

# ── Factory imports ────────────────────────────────────────────────────────────
from source.factory import DataSourceFactory
from chunking.factory import ChunkingFactory
from embedding.factory import EmbeddingFactory
from extractors.factory import ExtractorFactory
from query.factory import QueryFactory

# ── LlamaIndex ────────────────────────────────────────────────────────────────
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.faiss import FaissVectorStore

from extractors.ocr_config import configure_tesseract
from vector_store.factory import VectorStoreFactory   #added this line
from llama_index.core.base.embeddings.base import BaseEmbedding #added this line
from typing import List
 

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

def load_config() -> dict:
    """Load and return config.yaml as a plain dict."""
    config_path = SCRIPT_DIR / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Step 1: Source ─────────────────────────────────────────────────────────────

def download_source_files(config: dict) -> list[str]:
    """
    Use DataSourceFactory to create the configured source and download files.

    The source type is read from ``config["source"]["type"]``.
    Supported: local | s3 | azure_blob | gdrive | sharepoint | web
    """
    source = DataSourceFactory.create(config)
    files = source.download()

    if not files:
        print("[main] No files were downloaded from the configured source.")

    return files


# ── Step 2: Extract ────────────────────────────────────────────────────────────

def extract_documents(file_paths: list[str], source_type: str) -> list[Document]:
    """
    Run each file through the ExtractorFactory and return valid Documents.

    The extractor is selected by file extension (PDF, DOCX, XLSX, etc.).
    Files with less than 10 non-whitespace characters are skipped.
    """
    documents: list[Document] = []

    for file_path in file_paths:
        try:
            extractor = ExtractorFactory.get_extractor(file_path)
            text = extractor.extract_text(file_path)

            if not text or len(text.strip()) < 10:
                print(f"[main] Skipping empty/short document: {file_path}")
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


# ── Step 3: Chunk ──────────────────────────────────────────────────────────────

def chunk_documents(documents: list[Document], config: dict) -> list[BaseNode]:
    """
    Use ChunkingFactory to create the configured chunker and split documents.

    The strategy is read from ``config["chunking"]["strategy"]``.
    Supported: sentence | token | character | recursive | semantic
    """
    chunker = ChunkingFactory.create(config)
    nodes = chunker.chunk(documents)

    print(f"\n[main] Total nodes (chunks) created: {len(nodes)}")

    # Debug: print first node structure
    if nodes:
        first = nodes[0]
        print("\n--- SAMPLE NODE ---")
        try:
            print(json.dumps(first.to_dict(), indent=2)[:800])
        except Exception:
            print(first.text[:400] if hasattr(first, "text") else str(first)[:400])

    return nodes


# ── Step 4: Embed & Index ──────────────────────────────────────────────────────

def build_vector_index(nodes: list[BaseNode], config: dict) -> VectorStoreIndex:
    """
    Use EmbeddingFactory to create the configured embedder, then build a
    FAISS VectorStoreIndex from the provided nodes.

    The provider is read from ``config["embedding"]["provider"]``.
    """
    # Validate API key if OpenAI is selected
    embedding_provider = config["embedding"]["provider"].lower()
    if embedding_provider in ("openai", "azure_openai"):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "[main] OPENAI_API_KEY environment variable is not set. "
                "Add it to your .env file."
            )

    # ── EmbeddingFactory: creates the right embedder from config ──────────────
    embedder = EmbeddingFactory.create(config)
    print(f"[main] Embedder ready: {embedder}")

    # ── Wrap as a LlamaIndex-compatible embed_model ────────────────────────────
    # For providers other than OpenAI we need to adapt the BaseEmbedder
    # to the LlamaIndex interface.  For now OpenAI uses the native adapter.
    from llama_index.embeddings.openai import OpenAIEmbedding as _OAIEmbed

    dimensions = config["embedding"]["dimensions"]
    model_name = config["embedding"]["model"]
    
    if embedding_provider == "openai":
        llama_embed_model = _OAIEmbed(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=model_name,
        )
    else:
        # Generic adapter: wraps our BaseEmbedder into the LlamaIndex interface
        llama_embed_model = _BaseEmbedderAdapter(embedder)

    # ── FAISS index ────────────────────────────────────────────────────────────    
    # Dynamic vector store from config    
    # Dynamic vector store from config
    vector_store = VectorStoreFactory.create(config)
    vector_store.connect()

    print(f"[main] Vector store ready: {vector_store}")
    index = VectorStoreIndex(
        nodes,
        embed_model=llama_embed_model,
        vector_store=vector_store,
    )

    return index


class _BaseEmbedderAdapter(BaseEmbedding):
    """
    Minimal adapter that wraps a ``BaseEmbedder`` so LlamaIndex can call it
    as an embed_model.  Covers the two methods LlamaIndex uses during indexing.
    """

    def __init__(self, embedder):
        self._embedder = embedder

    def get_text_embedding(self, text: str) -> list[float]:
        return self._embedder.embed_query(text)

    def get_text_embedding_batch(
        self, texts: list[str], show_progress: bool = False
    ) -> list[list[float]]:
        return self._embedder.embed_texts(texts)

    # LlamaIndex also calls this for query embedding
    def get_query_embedding(self, query: str) -> list[float]:
        return self._embedder.embed_query(query)

    def get_agg_embedding_from_queries(self, queries, agg_fn=None):
        vecs = [self.get_query_embedding(q) for q in queries]
        if agg_fn:
            return agg_fn(vecs)
        # Default: average
        if not vecs:
            return []
        dim = len(vecs[0])
        avg = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
        return avg


# ── Pipeline orchestrator ──────────────────────────────────────────────────────
def run_pipeline(config: dict) -> VectorStoreIndex:
    """
    Run the full RAG ingestion pipeline:
        1. Download  → DataSourceFactory  (source.type)
        2. Extract   → ExtractorFactory   (file extension)
        3. Chunk     → ChunkingFactory    (chunking.strategy)
        4. Embed     → EmbeddingFactory   (embedding.provider)
        5. Index     → FAISS VectorStore
    """
    # Step 1
    print("\n" + "=" * 60)
    print("Step 1: Downloading files from the configured source...")
    print(f"        source.type = {config['source']['type']!r}")
    files = download_source_files(config)

    if not files:
        raise SystemExit("[main] No files downloaded. Check source config.")

    # Step 2
    print("\n" + "=" * 60)
    print("Step 2: Extracting text from documents...")
    documents = extract_documents(files, config["source"]["type"])
    print(f"        Valid documents: {len(documents)}")

    if not documents:
        raise SystemExit("[main] No valid documents after extraction.")

    # Step 3
    print("\n" + "=" * 60)
    print("Step 3: Chunking documents...")
    print(f"        chunking.strategy = {config['chunking'].get('strategy', 'sentence')!r}")
    nodes = chunk_documents(documents, config)

    # Step 4
    print("\n" + "=" * 60)
    print("Step 4: Building vector index...")
    print(f"        embedding.provider = {config['embedding']['provider']!r}")
    index = build_vector_index(nodes, config)
    print("        Index built successfully.")

    return index


# ── Step 5: Query ─────────────────────────────────────────────────────────────

def run_query(query_text: str, index, config: dict):
    """
    Use QueryFactory to create the configured query strategy and execute it.

    The strategy is read from ``config["query_mode"]["strategy"]``.
    Supported: rag | query_only | hybrid

    Output format (table|chart|form|text) is decided by QueryPlanner
    using rules + optional LLM, then rendered by QueryExecutor.
    """
    if not config.get("query_mode", {}).get("enabled", True):
        print("[main] query_mode.enabled is false — skipping query step.")
        return None

    strategy = QueryFactory.create(config)
    print(f"[main] Query strategy: {strategy}")

    result = strategy.execute(query_text, index)

    print("\n--- QUERY RESULT ---")
    print(f"Strategy : {result.strategy}")
    print(f"Format   : {result.output_format}")
    print(f"Answer   :\n{result.answer[:800]}")

    if result.rendered and result.output_format != "text":
        print(f"\n--- RENDERED ({result.output_format.upper()}) ---")
        print(str(result.rendered)[:600])

    return result


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    config = load_config()

    print("\n" + "=" * 60)
    print("Pipeline factories loaded from config.yaml:")
    print(f"  source.type          = {config['source']['type']!r}")
    print(f"  chunking.strategy    = {config['chunking'].get('strategy', 'sentence')!r}")
    print(f"  embedding.provider   = {config['embedding']['provider']!r}")
    print(f"  query_mode.strategy  = {config.get('query_mode', {}).get('strategy', 'hybrid')!r}")
    print(f"  query_planner.model  = {config.get('query_planner', {}).get('model', 'qwen-mini')!r}")

    # Steps 1–4: ingest + embed + index
    index = run_pipeline(config)

    # Step 5: query via QueryFactory
    sample_query = "Summarize the documents"
    print("\n" + "=" * 60)
    print(f"Step 5: Running query via QueryFactory...")
    print(f"        query_mode.strategy = {config.get('query_mode', {}).get('strategy', 'hybrid')!r}")
    run_query(sample_query, index, config)


if __name__ == "__main__":
    main()
