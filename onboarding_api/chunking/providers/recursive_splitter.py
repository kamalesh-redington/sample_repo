from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import List

from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from chunking.base import BaseChunker, ChunkingConfig

_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class RecursiveChunker(BaseChunker):

    def __init__(self, config: ChunkingConfig):

        super().__init__(config)

        self.chunk_size: int = config.chunk_size

        self.chunk_overlap: int = min(config.chunk_overlap, config.chunk_size - 1)

        self.separators: List[str] = config.extra.get("separators", _DEFAULT_SEPARATORS)

        logger.info("Initializing RecursiveChunker")

        logger.debug(f"Recursive chunk size: {config.chunk_size}")

        logger.debug(f"Recursive overlap: {config.chunk_overlap}")

        logger.debug(f"Recursive separators: {self.separators}")

    def _split(self, text: str, separators: List[str]) -> List[str]:

        logger.debug(f"Recursive splitting text length: {len(text)}")

        if not text:
            return []

        sep = separators[0]

        next_seps = separators[1:]

        if sep == "":
            raw_parts = list(text)
        else:
            raw_parts = text.split(sep)

        pieces: List[str] = []

        for part in raw_parts:

            part = part.strip()

            if not part:
                continue

            if len(part) <= self.chunk_size:

                pieces.append(part)

            elif next_seps:

                pieces.extend(self._split(part, next_seps))

            else:

                for i in range(0, len(part), self.chunk_size - self.chunk_overlap):

                    pieces.append(part[i : i + self.chunk_size])

        return self._merge(pieces)

    def _merge(self, pieces: List[str]) -> List[str]:

        logger.debug(f"Merging recursive pieces count: {len(pieces)}")

        chunks: List[str] = []

        current = ""

        for piece in pieces:

            candidate = (current + " " + piece).strip() if current else piece

            if len(candidate) <= self.chunk_size:

                current = candidate

            else:

                if current:
                    chunks.append(current)

                if self.chunk_overlap > 0 and len(current) >= self.chunk_overlap:

                    current = current[-self.chunk_overlap :] + " " + piece

                else:

                    current = piece

        if current:
            chunks.append(current)

        return chunks

    def chunk(self, documents: List[Document]) -> List[BaseNode]:

        try:

            logger.info(f"Starting recursive chunking for {len(documents)} document(s)")

            nodes: List[BaseNode] = []

            for doc in documents:

                text = doc.text or ""

                chunks = self._split(text, self.separators)

                for i, chunk_text in enumerate(chunks):

                    meta = {**doc.metadata, "chunk_index": i}

                    node = TextNode(
                        text=chunk_text,
                        metadata=meta,
                        id_=f"{doc.doc_id}_rec_{i}",
                    )

                    nodes.append(node)

            logger.info("Recursive chunking completed successfully")

            logger.debug(f"Generated recursive nodes: {len(nodes)}")

            return nodes

        except Exception as e:

            logger.exception("Recursive chunking failed")

            raise
