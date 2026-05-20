from config.logger import setup_logger

logger = setup_logger(__name__)

import os

from pathlib import Path

from typing import List

from source.base import DataSource
from source.utils import ensure_dir


class AzureBlobSource(DataSource):

    def __init__(self, config: dict):

        logger.info("Initializing AzureBlobSource")

        src = config["source"]

        self.container: str = src["container"]

        self.prefix: str = src.get("prefix", "")

        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        logger.debug(f"Azure container: {self.container}")

        logger.debug(f"Azure prefix: {self.prefix}")

        ensure_dir(self.local_dir)

        raw_conn = src.get("connection_string", "")

        self.connection_string: str = self._resolve_connection_string(raw_conn)

        logger.info("AzureBlobSource initialized successfully")

    @staticmethod
    def _resolve_connection_string(raw: str) -> str:

        import re

        logger.debug("Resolving Azure connection string")

        def _expand(match):

            var = match.group(1)

            val = os.environ.get(var)

            if val is None:

                logger.warning(f"Missing Azure environment variable: {var}")

                raise EnvironmentError(
                    f"[AzureBlobSource] Environment variable '{var}' is not set."
                )

            return val

        expanded = re.sub(r"\$\{?([A-Z_][A-Z0-9_]*)\}?", _expand, raw) if raw else ""

        if expanded:

            logger.info("Azure connection string resolved from config/env")

            return expanded

        conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")

        if conn:

            logger.info("Azure connection string loaded from environment")

            return conn

        account = os.environ.get("AZURE_STORAGE_ACCOUNT")

        key = os.environ.get("AZURE_STORAGE_KEY")

        if account and key:

            logger.info("Building Azure connection string from account credentials")

            return (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={account};"
                f"AccountKey={key};"
                f"EndpointSuffix=core.windows.net"
            )

        logger.exception("Azure credentials not found")

        raise EnvironmentError(
            "[AzureBlobSource] No Azure connection string or account credentials found."
        )

    def _get_client(self):

        try:

            logger.info("Creating Azure Blob client")

            from azure.storage.blob import BlobServiceClient

        except ImportError as exc:

            logger.exception("azure-storage-blob import failed")

            raise ImportError(
                "azure-storage-blob required → pip install azure-storage-blob"
            ) from exc

        return BlobServiceClient.from_connection_string(self.connection_string)

    def download(self) -> List[str]:

        try:

            logger.info("Starting Azure Blob download process")

            client = self._get_client()

            container_client = client.get_container_client(self.container)

            downloaded_files: List[str] = []

            logger.info(f"Listing Azure blobs in container='{self.container}'")

            blobs = list(container_client.list_blobs(name_starts_with=self.prefix))

            if not blobs:

                logger.warning("No Azure blobs found")

                return []

            for blob in blobs:

                blob_name: str = blob.name

                if blob_name.endswith("/"):

                    logger.debug(f"Skipping virtual directory: {blob_name}")

                    continue

                relative = (
                    blob_name[len(self.prefix) :].lstrip("/")
                    if self.prefix
                    else blob_name
                )

                local_path = self.local_dir / relative

                ensure_dir(local_path.parent)

                try:

                    logger.debug(f"Downloading Azure blob: {blob_name}")

                    blob_client = container_client.get_blob_client(blob_name)

                    with open(local_path, "wb") as f:

                        stream = blob_client.download_blob()

                        stream.readinto(f)

                    downloaded_files.append(str(local_path))

                    logger.info(f"Downloaded Azure blob: {blob_name}")

                except Exception as exc:

                    logger.exception(f"Azure blob download failed: {blob_name}")

            logger.info(
                f"Azure Blob download completed → {len(downloaded_files)} file(s)"
            )

            return downloaded_files

        except Exception as e:

            logger.exception("Azure Blob download process failed")

            raise
