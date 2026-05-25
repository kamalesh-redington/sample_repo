from config.logger import setup_logger

logger = setup_logger(__name__)

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from .base import DocumentExtractor


class ExcelExtractor(DocumentExtractor):

    def _flatten_json(self, data, parent_key=""):
        """
        Recursively flatten nested JSON structures.
        """
        items = []

        if isinstance(data, dict):

            for key, value in data.items():

                new_key = (
                    f"{parent_key}.{key}"
                    if parent_key
                    else key
                )

                items.extend(
                    self._flatten_json(value, new_key)
                )

        elif isinstance(data, list):

            for index, value in enumerate(data):

                new_key = f"{parent_key}[{index}]"

                items.extend(
                    self._flatten_json(value, new_key)
                )

        else:

            items.append(
                f"{parent_key}: {data}"
            )

        return items

    def extract_text(self, file_path: str) -> str:

        try:

            logger.info(
                f"Starting file extraction: {file_path}"
            )

            extension = (
                Path(file_path)
                .suffix
                .strip()
                .lower()
            )

            logger.info(
                f"Detected file extension: {extension}"
            )

            text_parts = []

            # ==========================================
            # CSV FILE
            # ==========================================
            if extension == ".csv":

                logger.info("Detected CSV file")

                df = pd.read_csv(file_path)

                df = df.fillna("")

                logger.debug(
                    f"CSV row count: {len(df)}"
                )

                text_parts.append(
                    "=== CSV DATA ==="
                )

                for _, row in df.iterrows():

                    row_text = ", ".join(
                        [
                            f"{col}: {row[col]}"
                            for col in df.columns
                        ]
                    )

                    text_parts.append(row_text)

            # ==========================================
            # EXCEL FILE
            # ==========================================
            elif extension in [".xlsx", ".xls"]:

                logger.info(
                    "Detected Excel file"
                )

                workbook = pd.read_excel(
                    file_path,
                    sheet_name=None
                )

                logger.debug(
                    f"Workbook sheets loaded: {list(workbook.keys())}"
                )

                for sheet_name, df in workbook.items():

                    logger.info(
                        f"Processing Excel sheet: {sheet_name}"
                    )

                    df = df.fillna("")

                    logger.debug(
                        f"Sheet row count: {len(df)}"
                    )

                    text_parts.append(
                        f"\n=== Sheet: {sheet_name} ==="
                    )

                    for _, row in df.iterrows():

                        row_text = ", ".join(
                            [
                                f"{col}: {row[col]}"
                                for col in df.columns
                            ]
                        )

                        text_parts.append(
                            row_text
                        )

            # ==========================================
            # JSON FILE
            # ==========================================
            elif extension == ".json":

                logger.info(
                    "Detected JSON file"
                )

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)

                flattened_data = (
                    self._flatten_json(data)
                )

                logger.debug(
                    f"Flattened JSON entries: {len(flattened_data)}"
                )

                text_parts.append(
                    "=== JSON DATA ==="
                )

                text_parts.extend(
                    flattened_data
                )

            # ==========================================
            # XML FILE
            # ==========================================
            elif extension == ".xml":

                logger.info(
                    "Detected XML file"
                )

                tree = ET.parse(file_path)

                root = tree.getroot()

                text_parts.append(
                    "=== XML DATA ==="
                )

                extracted_count = 0

                for elem in root.iter():

                    if (
                        elem.text
                        and elem.text.strip()
                    ):

                        text_parts.append(
                            f"{elem.tag}: {elem.text.strip()}"
                        )

                        extracted_count += 1

                logger.debug(
                    f"XML elements extracted: {extracted_count}"
                )

            # ==========================================
            # UNSUPPORTED FILE
            # ==========================================
            else:

                logger.error(
                    f"Unsupported file format detected: {extension}"
                )

                raise ValueError(
                    f"Unsupported file format: {extension}"
                )

            final_text = (
                "\n".join(text_parts)
                .strip()
            )

            logger.info(
                f"File extraction completed successfully: {file_path}"
            )

            logger.debug(
                f"Extracted text length: {len(final_text)}"
            )

            return final_text

        except Exception:

            logger.exception(
                f"File extraction failed: {file_path}"
            )

            raise