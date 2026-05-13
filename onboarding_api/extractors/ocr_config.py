import os
import pytesseract

def configure_tesseract():
    tesseract_path = os.getenv("TESSERACT_CMD")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
        print("Warning: TESSERACT_CMD not set. Using system PATH.")