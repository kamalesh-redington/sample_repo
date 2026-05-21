from config.logger import setup_logger

logger = setup_logger(__name__)

import pandas as pd

from .base import DocumentExtractor


class ExcelExtractor(DocumentExtractor):

    def extract_text(self, file_path: str) -> str:

        try:

            logger.info(f"Starting Excel extraction: {file_path}")

            workbook = pd.read_excel(file_path, sheet_name=None)

            logger.debug(f"Workbook sheets loaded: {list(workbook.keys())}")

            text_parts = []

            for sheet_name, df in workbook.items():

                logger.info(f"Processing Excel sheet: {sheet_name}")

                df = df.fillna("")

                logger.debug(f"Sheet row count: {len(df)}")

                text_parts.append(f"\n=== Sheet: {sheet_name} ===")

                for _, row in df.iterrows():

                    row_text = ", ".join([f"{col}: {row[col]}" for col in df.columns])

                    text_parts.append(row_text)

            final_text = "\n".join(text_parts).strip()

            logger.info(f"Excel extraction completed successfully: {file_path}")

            logger.debug(f"Extracted text length: {len(final_text)}")

            return final_text

        except Exception as e:

            logger.exception(f"Excel extraction failed: {file_path}")

            raise
