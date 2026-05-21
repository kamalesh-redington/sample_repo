# Onboarding API — Project Directory

This repository contains the Onboarding API and supporting modules for content extraction, chunking, embedding, and vector stores.

## Project Overview
- Short: Directory tree and one-line descriptions for each file/folder in the project.

## Top-level files
- [app.py](app.py): Application entry / orchestration script (likely starts API or main app).
- [chunks_output.txt](chunks_output.txt): Generated chunked-text artifact.
- [config.yaml](config.yaml): Global configuration (app/tenant settings).
- [flow.txt](flow.txt): Workflow notes or processing steps.
- [main.py](main.py): Alternate entrypoint / runner script.
- [onboarding_api_directory.txt](onboarding_api_directory.txt): Project directory snapshot or notes.
- [requirements.txt](requirements.txt): Python dependencies.
- [sample.py](sample.py): Example usage script or snippet.
- [streamlit_app.py](streamlit_app.py): Streamlit demo UI application.
- [test.txt](test.txt): Misc test output or notes.

## auth/
- [auth/__init__.py](auth/__init__.py): Package initializer for `auth`.
- [auth/security.py](auth/security.py): Authentication / authorization utilities (tokens, guards).

## chunking/
- [chunking/__init__.py](chunking/__init__.py): Package initializer for `chunking`.
- [chunking/base.py](chunking/base.py): Base classes / interfaces for chunking logic.
- [chunking/factory.py](chunking/factory.py): Factory to create chunkers from config.
- `chunking/providers/`:
  - [chunking/providers/character_splitter.py](chunking/providers/character_splitter.py): Character-count based splitter.
  - [chunking/providers/recursive_splitter.py](chunking/providers/recursive_splitter.py): Recursive splitting algorithm.
  - [chunking/providers/semantic_splitter.py](chunking/providers/semantic_splitter.py): Semantic-aware splitting (meaning-based).
  - [chunking/providers/sentence_splitter.py](chunking/providers/sentence_splitter.py): Sentence-based splitting.
  - [chunking/providers/token_splitter.py](chunking/providers/token_splitter.py): Token-count based splitting.

## config/
- [config/logger.py](config/logger.py): Logging configuration and helper functions.

## timer.py
- [timer.py](timer.py): Timing utilities / stopwatch helpers.

## data/
- `data/` (folder): Data artifacts / temporary storage (contents not listed).

## db/
- [db/__init__.py](db/__init__.py): DB package initializer.
- [db/crud.py](db/crud.py): Create/Read/Update/Delete database helpers.
- [db/database.py](db/database.py): Database connection and session management.
- [db/models.py](db/models.py): ORM models / schema definitions.

## embedding/
- [embedding/__init__.py](embedding/__init__.py)
- [embedding/base.py](embedding/base.py): Base embedder interface and shared helpers.
- [embedding/factory.py](embedding/factory.py): Factory for embedding providers.
- `embedding/providers/`:
  - [embedding/providers/azure_openai_embedder.py](embedding/providers/azure_openai_embedder.py)
  - [embedding/providers/bedrock_embedder.py](embedding/providers/bedrock_embedder.py)
  - [embedding/providers/bm25_embedder.py](embedding/providers/bm25_embedder.py)
  - [embedding/providers/clip_embedder.py](embedding/providers/clip_embedder.py)
  - [embedding/providers/cohere_embedder.py](embedding/providers/cohere_embedder.py)
  - [embedding/providers/colbert_embedder.py](embedding/providers/colbert_embedder.py)
  - [embedding/providers/fastembed_embedder.py](embedding/providers/fastembed_embedder.py)
  - [embedding/providers/google_vertex_embedder.py](embedding/providers/google_vertex_embedder.py)
  - [embedding/providers/huggingface_embedder.py](embedding/providers/huggingface_embedder.py)
  - [embedding/providers/hybrid_embedder.py](embedding/providers/hybrid_embedder.py)
  - [embedding/providers/instructor_embedder.py](embedding/providers/instructor_embedder.py)
  - [embedding/providers/jina_embedder.py](embedding/providers/jina_embedder.py)
  - [embedding/providers/ollama_embedder.py](embedding/providers/ollama_embedder.py)
  - [embedding/providers/openai_embedder.py](embedding/providers/openai_embedder.py)
  - [embedding/providers/sentence_transformer_embedder.py](embedding/providers/sentence_transformer_embedder.py)
  - [embedding/providers/splade_embedder.py](embedding/providers/splade_embedder.py)
  - [embedding/providers/voyage_embedder.py](embedding/providers/voyage_embedder.py)

## extractors/
- [extractors/__init__.py](extractors/__init__.py)
- [extractors/base.py](extractors/base.py): Base extractor class and helpers.
- [extractors/excel_extractor.py](extractors/excel_extractor.py): Excel (.xls/.xlsx) extractor.
- [extractors/factory.py](extractors/factory.py): Extractor factory for file types.
- [extractors/image_extractor.py](extractors/image_extractor.py): Image preprocessing / extraction.
- [extractors/ocr_config.py](extractors/ocr_config.py): OCR provider/config helpers.
- [extractors/pdf_extractor.py](extractors/pdf_extractor.py): PDF text extraction.
- [extractors/ppt_extractor.py](extractors/ppt_extractor.py): PowerPoint extraction.
- [extractors/word_extractor.py](extractors/word_extractor.py): Word (.docx) extraction.

## logs/
- `logs/` (folder): Runtime logs storage.

## source/
- [source/__init__.py](source/__init__.py)
- [source/azure_blob_source.py](source/azure_blob_source.py): Azure Blob Storage source adapter.
- [source/base.py](source/base.py): Base source interface (list/download).
- [source/factory.py](source/factory.py): Source factory selecting provider.
- [source/gdrive_source.py](source/gdrive_source.py): Google Drive integration.
- [source/local_source.py](source/local_source.py): Local filesystem source adapter.
- [source/s3_source.py](source/s3_source.py): AWS S3 source integration.
- [source/sharepoint_source.py](source/sharepoint_source.py): SharePoint source integration.
- [source/utils.py](source/utils.py): Utilities for sources (path/URL helpers).
- [source/web_source.py](source/web_source.py): Web fetching / crawling source.

## tenant_configs/
- Tenant-specific YAMLs:
  - [tenant_configs/redington-ecommerce-9-config.yaml](tenant_configs/redington-ecommerce-9-config.yaml)
  - [tenant_configs/redington-ecommerce-10-config.yaml](tenant_configs/redington-ecommerce-10-config.yaml)
  - [tenant_configs/redington-ecommerce-11-config.yaml](tenant_configs/redington-ecommerce-11-config.yaml)
  - [tenant_configs/redington-ecommerce-12-config.yaml](tenant_configs/redington-ecommerce-12-config.yaml)
  - [tenant_configs/redington-ecommerce-13-config.yaml](tenant_configs/redington-ecommerce-13-config.yaml)
  - [tenant_configs/redington-ecommerce-14-config.yaml](tenant_configs/redington-ecommerce-14-config.yaml)
  - [tenant_configs/redington-ecommerce-15-config.yaml](tenant_configs/redington-ecommerce-15-config.yaml)
  - [tenant_configs/redington-ecommerce-16-config.yaml](tenant_configs/redington-ecommerce-16-config.yaml)
  - [tenant_configs/redington-ecommerce-17-config.yaml](tenant_configs/redington-ecommerce-17-config.yaml)
  - [tenant_configs/redington-ecommerce-18-config.yaml](tenant_configs/redington-ecommerce-18-config.yaml)

## vector_store/
- [vector_store/__init__.py](vector_store/__init__.py)
- [vector_store/base.py](vector_store/base.py): Vector store interface (save/query).
- [vector_store/factory.py](vector_store/factory.py): Factory to instantiate the configured store.
- `vector_store/stores/`:
  - [vector_store/stores/azure_blob_vector_store.py](vector_store/stores/azure_blob_vector_store.py)
  - [vector_store/stores/chroma_store.py](vector_store/stores/chroma_store.py)
  - [vector_store/stores/elasticsearch_store.py](vector_store/stores/elasticsearch_store.py)
  - [vector_store/stores/faiss_store.py](vector_store/stores/faiss_store.py)
  - [vector_store/stores/gcs_vector_store.py](vector_store/stores/gcs_vector_store.py)
  - [vector_store/stores/milvus_store.py](vector_store/stores/milvus_store.py)
  - [vector_store/stores/pgvector_store.py](vector_store/stores/pgvector_store.py)
  - [vector_store/stores/pinecone_store.py](vector_store/stores/pinecone_store.py)
  - [vector_store/stores/qdrant_store.py](vector_store/stores/qdrant_store.py)
  - [vector_store/stores/s3_vector_store.py](vector_store/stores/s3_vector_store.py)
  - [vector_store/stores/weaviate_store.py](vector_store/stores/weaviate_store.py)

---

### Next steps
- Extract docstrings or top comments from key files to replace inferred descriptions.
- Add usage examples or run instructions.

If you want, I can extract the first docstring/comment from each file and update these descriptions.
