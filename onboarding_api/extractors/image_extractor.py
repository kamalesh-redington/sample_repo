from config.logger import setup_logger

logger = setup_logger(__name__)

from PIL import Image

import pytesseract

from .base import DocumentExtractor


class ImageExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:

        try:

            logger.info(f"Starting image OCR extraction: {file_path}")

            img = Image.open(file_path)

            logger.debug(f"Image opened successfully: {img.size}")

            text = pytesseract.image_to_string(img)

            logger.info(f"Image OCR extraction completed: {file_path}")

            logger.debug(f"Extracted text length: {len(text)}")

            return text.strip()

        except Exception as e:

            logger.exception(f"Image OCR extraction failed: {file_path}")

            raise
