from pathlib import Path
from config.logger import setup_logger

logger = setup_logger(__name__)

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
        logger.info(f"Selecting extractor for file type: {suffix}")
        extractor_cls = ExtractorFactory.MAPPING.get(suffix)

        if extractor_cls is None:
            logger.warning(f"Unsupported extractor type requested: {suffix}")
            raise ValueError(f"Unsupported file type: {suffix}")
        logger.info(f"Extractor selected: {extractor_cls.__name__}")
        logger.debug(f"Creating extractor instance for file: {file_path}")
        return extractor_cls()
