from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from chunking.base import BaseChunker, ChunkingConfig


class CharacterChunker(BaseChunker):

    def __init__(self, config: ChunkingConfig):

        super().__init__(config)

        logger.info("Initializing CharacterChunker")

        logger.debug(f"Character chunk size: {config.chunk_size}")

        logger.debug(f"Character chunk overlap: {config.chunk_overlap}")

        self.chunk_size: int = config.chunk_size

        self.chunk_overlap: int = min(config.chunk_overlap, config.chunk_size - 1)

    def _split_text(self, text: str) -> List[str]:

        logger.debug(f"Splitting text of length: {len(text)}")

        chunks: List[str] = []

        step = self.chunk_size - self.chunk_overlap

        start = 0

        while start < len(text):

            end = start + self.chunk_size

            chunks.append(text[start:end])

            start += step

            if start >= len(text):
                break

        logger.debug(f"Generated character chunks: {len(chunks)}")

        return chunks

    def chunk(self, documents: List[Document]) -> List[BaseNode]:

        try:

            logger.info(f"Starting character chunking for {len(documents)} document(s)")

            nodes: List[BaseNode] = []

            for doc in documents:

                logger.debug(f"Processing document ID: {doc.doc_id}")

                text = doc.text or ""

                chunks = self._split_text(text)

                for i, chunk_text in enumerate(chunks):

                    meta = {**doc.metadata, "chunk_index": i}

                    node = TextNode(
                        text=chunk_text,
                        metadata=meta,
                        id_=f"{doc.doc_id}_char_{i}",
                    )

                    nodes.append(node)

            logger.info("Character chunking completed successfully")

            logger.debug(f"Generated character nodes: {len(nodes)}")

            return nodes

        except Exception as e:

            logger.exception("Character chunking failed")

            raise
