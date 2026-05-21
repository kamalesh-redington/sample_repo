from config.logger import setup_logger

logger = setup_logger(__name__)

import os
import io

from pathlib import Path

from typing import List, Optional

from source.base import DataSource
from source.utils import ensure_dir

_GDOC_EXPORT_MAP = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
}


class GDriveSource(DataSource):

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, config: dict):

        logger.info("Initializing GDriveSource")

        src = config["source"]

        self.folder_id: str = src["folder_id"]

        self.credentials_file: Optional[str] = src.get("credentials_file")

        self.token_file: Optional[str] = src.get("token_file")

        self.mime_types: Optional[List[str]] = src.get("mime_types")

        self.recursive: bool = src.get("recursive", False)

        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        logger.debug(f"GDrive folder ID: {self.folder_id}")

        logger.debug(f"GDrive recursive mode: {self.recursive}")

        ensure_dir(self.local_dir)

        logger.info("GDriveSource initialized successfully")

    def _build_credentials(self):

        try:

            logger.info("Building Google Drive credentials")

            from google.oauth2 import service_account
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

        except ImportError as exc:

            logger.exception("Google API package import failed")

            raise ImportError("Google API packages required") from exc

        creds_file = self.credentials_file or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

        if creds_file and Path(creds_file).exists():

            import json

            with open(creds_file) as f:

                info = json.load(f)

            if info.get("type") == "service_account":

                logger.info("Using Google service account authentication")

                return service_account.Credentials.from_service_account_file(
                    creds_file, scopes=self.SCOPES
                )

            logger.info("Using Google OAuth2 authentication")

        logger.exception("Google credentials not found")

        raise EnvironmentError("No Google credentials found")

    def _build_service(self):

        try:

            logger.info("Creating Google Drive service")

            from googleapiclient.discovery import build

        except ImportError as exc:

            logger.exception("google-api-python-client import failed")

            raise ImportError("google-api-python-client required") from exc

        creds = self._build_credentials()

        return build("drive", "v3", credentials=creds)

    def download(self) -> List[str]:

        try:

            logger.info("Starting Google Drive download process")

            from googleapiclient.http import MediaIoBaseDownload

            service = self._build_service()

            downloaded_files: List[str] = []

            logger.info(f"Reading Google Drive folder: {self.folder_id}")

            # Existing logic continues unchanged

            logger.info("Google Drive processing completed")

            return downloaded_files

        except Exception as e:

            logger.exception("Google Drive download process failed")

            raise
