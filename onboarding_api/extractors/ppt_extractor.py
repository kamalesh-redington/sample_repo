from pptx import Presentation
from .base import DocumentExtractor


class PPTExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:
        prs = Presentation(file_path)

        text_parts = []

        for i, slide in enumerate(prs.slides):
            text_parts.append(f"\n--- Slide {i+1} ---")

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text_parts.append(shape.text)

        return "\n".join(text_parts).strip()