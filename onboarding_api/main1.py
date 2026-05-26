"""
main.py — ONBOARDING + INGESTION PIPELINE ONLY

Responsibilities:
1. Download source files
2. Extract text
3. Chunk documents
4. Generate embeddings
5. Build vector index
"""

import json
import os
import sys
from pathlib import Path
from typing import List

sys.stdout.reconfigure(encoding="utf-8")

import yaml
from dotenv import load_dotenv

from config.logger import setup_logger
from config.timer import log_execution_time

logger = setup_logger(__name__)

# Exception handler registration helper
def register_exception_handlers(app):
    """Register global exception handlers on the provided FastAPI app.

    This function is intentionally placed here so `app.py` can call it after
    creating the FastAPI `app` instance without introducing circular imports.
    """
    try:
        from fastapi import HTTPException
        from fastapi.exceptions import RequestValidationError
        #from core import exceptions as core_exceptions

        #app.add_exception_handler(HTTPException, core_exceptions.http_exception_handler)
        #app.add_exception_handler(RequestValidationError, core_exceptions.validation_exception_handler)
        #app.add_exception_handler(Exception, core_exceptions.generic_exception_handler)

        logger.info("Global exception handlers registered on app")
    except Exception:
        logger.exception("Failed to register exception handlers")

# ── Factory imports ────────────────────────────────────────────────────────────
from source.factory import DataSourceFactory
from chunking.factory import ChunkingFactory
from embedding.factory import EmbeddingFactory
from extractors.factory import ExtractorFactory
from vector_store.factory import VectorStoreFactory
from object_store.factory import ObjectStoreFactory

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

        logger.info(
            f"Environment variables loaded from: {_env_path}"
        )
        break
else:
    load_dotenv()
    logger.warning(
        "No .env file found in expected locations. "
        "Using system environment variables."
    )

# ── Config loader ──────────────────────────────────────────────────────────────

@log_execution_time(logger)
def load_config(config_path: str) -> dict:
    """
    Load tenant-specific YAML configuration.
    """

    logger.info(
        f"Loading tenant configuration | path={config_path}"
    )

    path = Path(config_path)

    if not path.exists():

        logger.error(
            f"Tenant configuration file not found | path={config_path}"
        )

        raise FileNotFoundError(
            f"Tenant config not found: {config_path}"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:

            config = yaml.safe_load(f)

        logger.info(
            "Tenant configuration loaded successfully."
        )

        return config

    except Exception:

        logger.exception(
            f"Failed loading configuration | path={config_path}"
        )

        raise


# ── Step 1: Download source files ─────────────────────────────────────────────

@log_execution_time(logger)
def download_source_files(config: dict) -> list[str]:
    """
    Download files from configured source.
    """

    source_type = config["source"]["type"]

    logger.info(
        f"Starting source download | source_type={source_type}"
    )

    source = DataSourceFactory.create(config)

    files = source.download()

    if not files:

        logger.warning(
            f"No files downloaded | source_type={source_type}"
        )

        return []

    logger.info(
        f"Source download completed | files_downloaded={len(files)}"
    )

    logger.debug(
        f"Downloaded files: {files}"
    )

    return files



# ── Step 2: Extract documents ─────────────────────────────────────────────────

@log_execution_time(logger)
def extract_documents(
    file_paths: list[str],
    source_type: str
) -> list[Document]:
    """
    Extract text from downloaded documents.
    """

    logger.info(
        f"Starting document extraction | total_files={len(file_paths)}"
    )

    documents: list[Document] = []

    for file_path in file_paths:

        try:
            logger.info(
                f"Processing document | file={file_path}"
            )

            extractor = ExtractorFactory.get_extractor(file_path)

            logger.debug(
                f"Extractor selected | "
                f"extractor={extractor.__class__.__name__}"
            )

            text = extractor.extract_text(file_path)

            if not text or len(text.strip()) < 10:

                logger.warning(
                    f"Skipping empty/invalid document | file={file_path}"
                )

                continue

            logger.info(
                f"Document extracted successfully | "
                f"file={Path(file_path).name}"
            )

            logger.debug(
                f"Extracted preview:\n{text}"
            )

            doc = Document(
                text=text,
                metadata={
                    "file_name": Path(file_path).name,
                    "file_path": file_path,
                    "source": source_type,
                },
            )

            documents.append(doc)

        except Exception:

            logger.exception(
                f"Document extraction failed | file={file_path}"
            )

    logger.info(
        f"Document extraction completed | "
        f"valid_documents={len(documents)}"
    )

    return documents


# ── Step 3: Chunk documents ───────────────────────────────────────────────────

@log_execution_time(logger)
def chunk_documents(
    documents: list[Document],
    config: dict
) -> list[BaseNode]:
    """
    Chunk documents using configured strategy.
    """

    strategy = config["chunking"]["strategy"]

    logger.info(
        f"Starting document chunking | strategy={strategy}"
    )

    chunker = ChunkingFactory.create(config)

    nodes = chunker.chunk(documents)

    logger.info(
        f"Chunking completed | total_chunks={len(nodes)}"
    )

    if nodes:

        first = nodes[0]

        logger.debug(
            "Sample chunk generated successfully."
        )

        try:
            logger.debug(
                json.dumps(first.to_dict(), indent=2)[:800]
            )

        except Exception:

            logger.debug(
                first.text[:400]
                if hasattr(first, "text")
                else str(first)[:400]
            )

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
    config: dict,
    object_store
) -> VectorStoreIndex:
    """
    Generate embeddings and create vector index.
    """

    embedding_provider = config["embedding"]["provider"].lower()

    logger.info(
        f"Initializing embedding pipeline | "
        f"provider={embedding_provider}"
    )

    if embedding_provider in ("openai", "azure_openai"):

        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:

            logger.error(
                "OPENAI_API_KEY environment variable missing."
            )

            raise ValueError(
                "OPENAI_API_KEY environment variable is not set."
            )

    logger.info(
        "Creating embedding model..."
    )

    embedder = EmbeddingFactory.create(config)

    logger.info(
        f"Embedder initialized | "
        f"embedder={embedder.__class__.__name__}"
    )

    from llama_index.embeddings.openai import OpenAIEmbedding

    model_name = config["embedding"]["model"]

    if embedding_provider == "openai":

        logger.info(
            f"Using native OpenAI embedding model | model={model_name}"
        )

        llama_embed_model = OpenAIEmbedding(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=model_name,
        )

    else:

        logger.info(
            f"Using custom embedding adapter | model={model_name}"
        )

        llama_embed_model = _BaseEmbedderAdapter(embedder)

    logger.info(
        "Connecting to vector store..."
    )

    vector_store = VectorStoreFactory.create(config)

    vector_store.connect()

    logger.info(
        f"Vector store connected successfully | "
        f"vector_store={vector_store.__class__.__name__}"
    )

    logger.info(
        f"Creating vector index | total_nodes={len(nodes)}"
    )

    # ==========================================
    # STORE CHUNKS + EMBEDDINGS + METADATA IN S3
    # ==========================================

    logger.info(
        "Uploading chunks, embeddings, and metadata to S3..."
    )

    for i, node in enumerate(nodes):

        chunk_text = node.text

        # ======================================
        # DOCUMENT ID
        # ======================================

        document_id = Path(
            node.metadata.get(
                "file_name",
                "unknown_document"
            )
        ).stem

        # ======================================
        # CHUNK ID
        # ======================================

        chunk_id = f"chunk_{i:05d}"

        # ======================================
        # GENERATE EMBEDDING
        # ======================================

        embedding = llama_embed_model.get_text_embedding(
            chunk_text
        )

        # Reuse embedding later
        node.embedding = embedding

        # ======================================
        # CHUNK OBJECT
        # ======================================

        chunk_data = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "text": chunk_text,
        }

        object_store.save_chunk(
            document_id=document_id,
            chunk_id=chunk_id,
            data=chunk_data
        )

        chunk_key = f"{document_id}/chunks/{chunk_id}.json"

        print(f"[main] Uploaded chunk → {chunk_key}")

        # ======================================
        # EMBEDDING OBJECT
        # ======================================

        embedding_data = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "embedding": embedding,
            "metadata": node.metadata,
        }

        object_store.save_embedding(
            document_id=document_id,
            chunk_id=chunk_id,
            data=embedding_data
        )

        embedding_key = f"{document_id}/embeddings/{chunk_id}.json"

        print(f"[main] Uploaded embedding → {embedding_key}")

        # ======================================
        # METADATA OBJECT
        # ======================================

        metadata_data = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "metadata": node.metadata,
        }

        object_store.save_metadata(
            document_id=document_id,
            chunk_id=chunk_id,
            data=metadata_data
        )

        metadata_key = f"{document_id}/metadata/{chunk_id}.json"
        
        print(f"[main] Uploaded metadata → {metadata_key}")

    logger.info(
    "S3 upload completed successfully."
    )

    # ==========================================
    # CREATE VECTOR INDEX
    # ==========================================

    index = VectorStoreIndex(
        nodes=nodes,
        embed_model=llama_embed_model,
        vector_store=vector_store,
    )

    logger.info(
        "Vector index created successfully."
    )

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

    logger.info("=" * 80)
    logger.info("INGESTION PIPELINE STARTED")
    logger.info("=" * 80)

    # Step 1
    logger.info(
        f"STEP 1 STARTED | source.type={config['source']['type']}"
    )

    files = download_source_files(config)

    if not files:

        logger.error(
            "Pipeline stopped | no files downloaded."
        )

        raise SystemExit("No files downloaded.")

    # Step 2
    logger.info("STEP 2 STARTED | document extraction")

    documents = extract_documents(
        files,
        config["source"]["type"]
    )

    logger.info(
        f"Document extraction completed | "
        f"valid_documents={len(documents)}"
    )

    if not documents:

        logger.error(
            "Pipeline stopped | no valid documents extracted."
        )

        raise SystemExit("No valid documents extracted.")

    # Step 3
    logger.info(
        f"STEP 3 STARTED | "
        f"chunking.strategy={config['chunking']['strategy']}"
    )

    nodes = chunk_documents(documents, config)


    # ==========================================
    # INITIALIZE S3 OBJECT STORE
    # ==========================================

    logger.info(
        "Initializing S3 object store..."
    )

    object_store = ObjectStoreFactory.create(config)

    object_store.connect()

    logger.info(
        "S3 object store initialized successfully."
    )

    # Step 4
    logger.info(
        f"STEP 4 STARTED | "
        f"embedding.provider={config['embedding']['provider']}"
    )

    index = build_vector_index(nodes, config, object_store)

    logger.info(
        "Ingestion pipeline completed successfully."
    )

    logger.info("=" * 80)

    return index


# ── Main entry point ──────────────────────────────────────────────────────────

@log_execution_time(logger)
def main():

    logger.info("=" * 80)
    logger.info("ONBOARDING + INGESTION PIPELINE")
    logger.info("=" * 80)

    config_path = SCRIPT_DIR / "config.yaml"

    logger.info(
        f"Resolved config path | path={config_path}"
    )

    config = load_config(str(config_path))

    logger.info(
        f"source.type={config['source']['type']}"
    )

    logger.info(
        f"chunking.strategy={config['chunking']['strategy']}"
    )

    logger.info(
        f"embedding.provider={config['embedding']['provider']}"
    )

    run_pipeline(config)

    logger.info(
        "Application execution completed successfully."
    )


if __name__ == "__main__":
    main()