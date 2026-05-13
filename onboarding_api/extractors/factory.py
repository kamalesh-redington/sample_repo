from pathlib import Path

from .pdf_extractor import PDFExtractor
from .excel_extractor import ExcelExtractor
from .word_extractor import WordExtractor
from .ppt_extractor import PPTExtractor
from .image_extractor import ImageExtractor

class ExtractorFactory:
    MAPPING = {
        "pdf": PDFExtractor,
        "xlsx": ExcelExtractor,
        "xls": ExcelExtractor,
        "json": ExcelExtractor,
        "csv": ExcelExtractor,
        "xml": ExcelExtractor,
        "docx": WordExtractor,
        "pptx": PPTExtractor,
        "png": ImageExtractor,
        "jpg": ImageExtractor,
        "jpeg": ImageExtractor,
    }

    @staticmethod
    def get_extractor(file_path: str):
        suffix = Path(file_path).suffix.lower().lstrip(".")

        extractor_cls = ExtractorFactory.MAPPING.get(suffix)

        if extractor_cls is None:
            raise ValueError(f"Unsupported file type: {suffix}")

        return extractor_cls()