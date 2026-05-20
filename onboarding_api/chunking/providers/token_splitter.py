from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from llama_index.core import Document
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import BaseNode

from chunking.base import BaseChunker, ChunkingConfig


class TokenChunker(BaseChunker):

    def __init__(self, config: ChunkingConfig):

        super().__init__(config)

        logger.info("Initializing TokenChunker")

        logger.debug(f"Token chunk size: {config.chunk_size}")

        logger.debug(f"Token chunk overlap: {config.chunk_overlap}")

        self._splitter = TokenTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def chunk(self, documents: List[Document]) -> List[BaseNode]:

        try:

            logger.info(f"Starting token chunking for {len(documents)} document(s)")

            nodes = self._splitter.get_nodes_from_documents(documents)

            logger.info("Token chunking completed successfully")

            logger.debug(f"Generated token nodes: {len(nodes)}")

            return nodes

        except Exception as e:

            logger.exception("Token chunking failed")

            raise
