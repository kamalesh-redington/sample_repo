from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode

from chunking.base import BaseChunker, ChunkingConfig


class SentenceChunker(BaseChunker):

    def __init__(self, config: ChunkingConfig):

        super().__init__(config)

        logger.info("Initializing SentenceChunker")

        logger.debug(f"Sentence chunk size: {config.chunk_size}")

        logger.debug(f"Sentence chunk overlap: {config.chunk_overlap}")

        self._splitter = SentenceSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def chunk(self, documents: List[Document]) -> List[BaseNode]:

        try:

            logger.info(f"Starting sentence chunking for {len(documents)} document(s)")

            nodes = self._splitter.get_nodes_from_documents(documents)

            logger.info(f"Sentence chunking completed successfully")

            logger.debug(f"Generated sentence nodes: {len(nodes)}")

            return nodes

        except Exception as e:

            logger.exception("Sentence chunking failed")

            raise
