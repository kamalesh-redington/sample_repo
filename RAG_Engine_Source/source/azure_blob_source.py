"""
AzureBlobSource — downloads blobs from Azure Blob Storage to a local directory.

Config schema (config.yaml → source section):
    source:
      type: azure_blob
      container: my-container          # required
      prefix: documents/               # optional folder prefix
      connection_string: ${AZURE_STORAGE_CONNECTION_STRING}  # env var or literal

Dependencies:
    pip install azure-storage-blob
"""

import os
from pathlib import Path
from typing import List

from source.base import DataSource
from source.utils import ensure_dir


class AzureBlobSource(DataSource):
    """
    Downloads files from an Azure Blob Storage container to a local directory.

    Authentication is resolved in this priority order:
        1. ``source.connection_string`` in config (env-var interpolation supported)
        2. ``AZURE_STORAGE_CONNECTION_STRING`` environment variable
        3. ``AZURE_STORAGE_ACCOUNT`` + ``AZURE_STORAGE_KEY`` environment variables
           (used to build a connection string automatically)
    """

    def __init__(self, config: dict):
        src = config["source"]
        self.container: str = src["container"]
        self.prefix: str = src.get("prefix", "")
        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)

        # Resolve connection string
        raw_conn = src.get("connection_string", "")
        self.connection_string: str = self._resolve_connection_string(raw_conn)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_connection_string(raw: str) -> str:
        """Expand env-var placeholders like ${VAR} and fall back to env vars."""
        import re

        def _expand(match):
            var = match.group(1)
            val = os.environ.get(var)
            if val is None:
                raise EnvironmentError(
                    f"[AzureBlobSource] Environment variable '{var}' is not set."
                )
            return val

        # Expand ${VAR} or $VAR patterns
        expanded = re.sub(r"\$\{?([A-Z_][A-Z0-9_]*)\}?", _expand, raw) if raw else ""

        if expanded:
            return expanded

        # Fall back to bare env var
        conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        if conn:
            return conn

        # Build from account + key
        account = os.environ.get("AZURE_STORAGE_ACCOUNT")
        key = os.environ.get("AZURE_STORAGE_KEY")
        if account and key:
            return (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={account};"
                f"AccountKey={key};"
                f"EndpointSuffix=core.windows.net"
            )

        raise EnvironmentError(
            "[AzureBlobSource] No Azure connection string or account credentials found. "
            "Set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT + AZURE_STORAGE_KEY."
        )

    def _get_client(self):
        """Lazily import and return a BlobServiceClient."""
        try:
            from azure.storage.blob import BlobServiceClient  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "azure-storage-blob is required for AzureBlobSource. "
                "Install it with: pip install azure-storage-blob"
            ) from exc
        return BlobServiceClient.from_connection_string(self.connection_string)

    # ------------------------------------------------------------------
    # DataSource interface
    # ------------------------------------------------------------------

    def download(self) -> List[str]:
        """
        List all blobs under ``container/prefix``, download each to
        ``local_dir``, and return a list of local file paths.
        """
        client = self._get_client()
        container_client = client.get_container_client(self.container)

        downloaded_files: List[str] = []

        print(
            f"[AzureBlobSource] Listing blobs in "
            f"container='{self.container}' prefix='{self.prefix}'"
        )

        blobs = list(container_client.list_blobs(name_starts_with=self.prefix))

        if not blobs:
            print("[AzureBlobSource] No blobs found.")
            return []

        for blob in blobs:
            blob_name: str = blob.name  # type: ignore

            # Skip virtual directory markers
            if blob_name.endswith("/"):
                continue

            # Preserve relative path structure under local_dir
            relative = blob_name[len(self.prefix):].lstrip("/") if self.prefix else blob_name
            local_path = self.local_dir / relative
            ensure_dir(local_path.parent)

            try:
                blob_client = container_client.get_blob_client(blob_name)
                with open(local_path, "wb") as f:
                    stream = blob_client.download_blob()
                    stream.readinto(f)

                downloaded_files.append(str(local_path))
                print(f"[AzureBlobSource] Downloaded: {blob_name} → {local_path}")

            except Exception as exc:
                print(f"[AzureBlobSource] Error downloading '{blob_name}': {exc}")

        print(f"[AzureBlobSource] Total downloaded: {len(downloaded_files)} file(s).")
        return downloaded_files
