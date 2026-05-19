import pandas as pd
from .base import DocumentExtractor

class ExcelExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:
        workbook = pd.read_excel(file_path, sheet_name=None)

        text_parts = []

        for sheet_name, df in workbook.items():
            text_parts.append(f"\n=== Sheet: {sheet_name} ===")

            df = df.fillna("")

            for _, row in df.iterrows():
                row_text = ", ".join(
                    [f"{col}: {row[col]}" for col in df.columns]
                )
                text_parts.append(row_text)

        return "\n".join(text_parts).strip()