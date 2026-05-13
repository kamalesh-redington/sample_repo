import docx
from .base import DocumentExtractor

class WordExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:
        document = docx.Document(file_path)

        text_parts = []

        for para in document.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Tables (important!)
        for table in document.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells]
                text_parts.append(" | ".join(row_text))

        return "\n".join(text_parts).strip()