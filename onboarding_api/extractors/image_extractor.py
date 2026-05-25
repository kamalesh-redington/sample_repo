from config.logger import setup_logger

logger = setup_logger(__name__)

from pathlib import Path
import fitz

from .pdf_extractor import PDFExtractor
from .base import DocumentExtractor


class ImageExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:

        try:

            logger.info(
                f"Starting image extraction: {file_path}"
            )

            pdf_path = str(
                Path(file_path).parent /
                f"{Path(file_path).stem}_temp.pdf"
            )

            # Create PDF from image using PyMuPDF
            image_doc = fitz.open(file_path)

            pdf_bytes = image_doc.convert_to_pdf()

            pdf_doc = fitz.open("pdf", pdf_bytes)

            pdf_doc.save(pdf_path)

            pdf_doc.close()
            image_doc.close()

            logger.info(
                f"Image converted to PDF: {pdf_path}"
            )

            # Reuse existing PDF extractor
            pdf_extractor = PDFExtractor()

            extracted_text = pdf_extractor.extract_text(
                pdf_path
            )

            logger.info(
                f"PDF extraction completed: {pdf_path}"
            )

            logger.debug(
                f"Extracted text length: {len(extracted_text)}"
            )

            return extracted_text.strip()

        except Exception:

            logger.exception(
                f"Image extraction failed: {file_path}"
            )

            raise