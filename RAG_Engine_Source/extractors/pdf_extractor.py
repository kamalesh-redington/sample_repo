import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path

from .base import DocumentExtractor


class PDFExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:
        text_parts = []

        # Step 1: Try PyMuPDF extraction
        try:
            doc = fitz.open(file_path)

            for page in doc:
                text = page.get_text("text")  # best general mode
                if text and text.strip():
                    text_parts.append(text)

        except Exception as e:
            print(f"PyMuPDF error: {e}")

        # Step 2: OCR fallback if no text extracted
        if not text_parts:
            print(f"OCR fallback triggered for: {file_path}")

            try:
                images = convert_from_path(file_path)

                for img in images:
                    ocr_text = pytesseract.image_to_string(img)
                    if ocr_text and ocr_text.strip():
                        text_parts.append(ocr_text)

            except Exception as e:
                print(f"OCR error: {e}")

        # Step 3: Final cleanup
        full_text = "\n".join(text_parts).strip()

        return full_text