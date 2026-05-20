from config.logger import setup_logger

logger = setup_logger(__name__)

import os
import pytesseract


def configure_tesseract():

    try:

        logger.info("Configuring Tesseract OCR")

        tesseract_path = os.getenv("TESSERACT_CMD")

        if tesseract_path:

            pytesseract.pytesseract.tesseract_cmd = tesseract_path

            logger.info(f"Tesseract path configured: {tesseract_path}")

        else:

            logger.warning("TESSERACT_CMD not set, using system PATH")

    except Exception as e:

        logger.exception("Tesseract configuration failed")

        raise
