from config.logger import setup_logger

logger = setup_logger(__name__)

import docx

from .base import DocumentExtractor


class WordExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:

        try:

            logger.info(f"Starting Word document extraction: {file_path}")

            document = docx.Document(file_path)

            logger.debug("Word document loaded successfully")

            text_parts = []

            # Paragraph extraction
            for para in document.paragraphs:

                if para.text.strip():

                    text_parts.append(para.text)

            logger.debug(f"Paragraph count extracted: {len(document.paragraphs)}")

            # Table extraction
            for table in document.tables:

                for row in table.rows:

                    row_text = [cell.text.strip() for cell in row.cells]

                    text_parts.append(" | ".join(row_text))

            logger.debug(f"Table count extracted: {len(document.tables)}")

            final_text = "\n".join(text_parts).strip()

            logger.info(f"Word extraction completed successfully: {file_path}")

            logger.debug(f"Extracted text length: {len(final_text)}")

            return final_text

        except Exception as e:

            logger.exception(f"Word extraction failed: {file_path}")

            raise
