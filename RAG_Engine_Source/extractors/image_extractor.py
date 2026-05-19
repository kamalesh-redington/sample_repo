from PIL import Image
import pytesseract
from .base import DocumentExtractor


class ImageExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:
        img = Image.open(file_path)

        text = pytesseract.image_to_string(img)

        return text.strip()