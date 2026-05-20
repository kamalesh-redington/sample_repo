from config.logger import setup_logger

logger = setup_logger(__name__)

import fitz  # PyMuPDF
import pytesseract

from pdf2image import convert_from_path

from .base import DocumentExtractor


class PDFExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:

        try:

            logger.info(f"Starting PDF extraction: {file_path}")

            text_parts = []

            # ────────────────────────────────────────────────────────────────
            # Step 1: PyMuPDF Extraction
            # ────────────────────────────────────────────────────────────────

            try:

                logger.info("Attempting PyMuPDF text extraction")

                doc = fitz.open(file_path)

                logger.debug(f"PDF opened successfully with {len(doc)} pages")

                for index, page in enumerate(doc):

                    logger.debug(f"Extracting text from PDF page: {index + 1}")

                    text = page.get_text("text")

                    if text and text.strip():

                        text_parts.append(text)

                logger.info("PyMuPDF extraction completed")

            except Exception as e:

                logger.exception("PyMuPDF extraction failed")

            # ────────────────────────────────────────────────────────────────
            # Step 2: OCR Fallback
            # ────────────────────────────────────────────────────────────────

            if not text_parts:

                logger.warning(f"OCR fallback triggered for PDF: {file_path}")

                try:

                    images = convert_from_path(file_path)

                    logger.debug(f"Converted PDF to {len(images)} image pages")

                    for index, img in enumerate(images):

                        logger.debug(f"Running OCR on page image: {index + 1}")

                        ocr_text = pytesseract.image_to_string(img)

                        if ocr_text and ocr_text.strip():

                            text_parts.append(ocr_text)

                    logger.info("OCR extraction completed successfully")

                except Exception as e:

                    logger.exception("OCR extraction failed")

            # ────────────────────────────────────────────────────────────────
            # Final Cleanup
            # ────────────────────────────────────────────────────────────────

            full_text = "\n".join(text_parts).strip()

            logger.info(f"PDF extraction completed successfully: {file_path}")

            logger.debug(f"Extracted text length: {len(full_text)}")

            return full_text

        except Exception as e:

            logger.exception(f"PDF extraction pipeline failed: {file_path}")

            raise
