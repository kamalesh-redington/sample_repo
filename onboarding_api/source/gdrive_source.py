"""
GDriveSource — downloads files from a Google Drive folder to a local directory.

Config schema (config.yaml → source section):
    source:
      type: gdrive
      folder_id: 1AbcXyzFolderIdFromDriveURL   # required
      credentials_file: ./gdrive_service_account.json  # service account JSON
      # OR for OAuth2 (interactive / token file):
      # token_file: ./gdrive_token.json
      mime_types:                               # optional MIME filter
        - application/pdf
        - application/vnd.openxmlformats-officedocument.wordprocessingml.document
      recursive: false                          # whether to recurse into sub-folders

Dependencies:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import os
from pathlib import Path
from typing import List, Optional

from source.base import DataSource
from source.utils import ensure_dir


# Google Drive export map: native GDocs MIME → exportable MIME + extension
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
    """
    Downloads files from a Google Drive folder.

    Authentication modes (resolved in order):
        1. Service account — ``source.credentials_file`` (JSON key file)
        2. OAuth2 token    — ``source.token_file`` (pre-authorized token.json)
        3. Environment var — ``GOOGLE_APPLICATION_CREDENTIALS`` path

    Google native formats (Docs, Sheets, Slides) are auto-exported to their
    Office equivalents so the downstream extractors can handle them.
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, config: dict):
        src = config["source"]
        self.folder_id: str = src["folder_id"]
        self.credentials_file: Optional[str] = src.get("credentials_file")
        self.token_file: Optional[str] = src.get("token_file")
        self.mime_types: Optional[List[str]] = src.get("mime_types")
        self.recursive: bool = src.get("recursive", False)
        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def _build_credentials(self):
        """Return google.oauth2 credentials based on available config."""
        try:
            from google.oauth2 import service_account  # type: ignore
            from google.oauth2.credentials import Credentials  # type: ignore
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
            from google.auth.transport.requests import Request  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Google API packages are required for GDriveSource. Install with:\n"
                "  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            ) from exc

        creds_file = (
            self.credentials_file
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )

        if creds_file and Path(creds_file).exists():
            # Detect service account vs OAuth2 client secrets
            import json
            with open(creds_file) as f:
                info = json.load(f)

            if info.get("type") == "service_account":
                print(f"[GDriveSource] Using service account: {creds_file}")
                return service_account.Credentials.from_service_account_file(
                    creds_file, scopes=self.SCOPES
                )
            else:
                # OAuth2 client secrets — try loading existing token first
                if self.token_file and Path(self.token_file).exists():
                    creds = Credentials.from_authorized_user_file(
                        self.token_file, self.SCOPES
                    )
                    if creds and creds.valid:
                        return creds
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        return creds

                # Interactive OAuth2 flow (requires browser)
                print("[GDriveSource] Starting OAuth2 flow (browser will open)...")
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, self.SCOPES)
                creds = flow.run_local_server(port=0)

                if self.token_file:
                    with open(self.token_file, "w") as token:
                        token.write(creds.to_json())
                    print(f"[GDriveSource] Token saved to {self.token_file}")
                return creds

        raise EnvironmentError(
            "[GDriveSource] No Google credentials found. "
            "Set 'source.credentials_file' or GOOGLE_APPLICATION_CREDENTIALS."
        )

    def _build_service(self):
        """Build and return the Google Drive API service object."""
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "google-api-python-client is required. "
                "Install with: pip install google-api-python-client"
            ) from exc

        creds = self._build_credentials()
        return build("drive", "v3", credentials=creds)

    # ------------------------------------------------------------------
    # Drive listing helpers
    # ------------------------------------------------------------------

    def _list_files(self, service, folder_id: str) -> List[dict]:
        """Recursively (or not) list all files in a Drive folder."""
        query_parts = [f"'{folder_id}' in parents", "trashed = false"]

        if self.mime_types:
            mime_clauses = " or ".join(
                f"mimeType = '{m}'" for m in self.mime_types
            )
            # Always include folders so we can recurse
            query_parts.append(
                f"(mimeType = 'application/vnd.google-apps.folder' or {mime_clauses})"
            )

        query = " and ".join(query_parts)
        files: List[dict] = []
        page_token = None

        while True:
            resp = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageToken=page_token,
                )
                .execute()
            )

            for item in resp.get("files", []):
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    if self.recursive:
                        files.extend(self._list_files(service, item["id"]))
                else:
                    files.append(item)

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return files

    # ------------------------------------------------------------------
    # DataSource interface
    # ------------------------------------------------------------------

    def download(self) -> List[str]:
        """
        List all files in the configured Drive folder and download each.
        Native Google formats are exported to Office-compatible formats.
        Returns a list of local file paths.
        """
        try:
            from googleapiclient.http import MediaIoBaseDownload  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "google-api-python-client is required. "
                "Install with: pip install google-api-python-client"
            ) from exc

        import io

        service = self._build_service()

        print(
            f"[GDriveSource] Listing files in folder_id='{self.folder_id}' "
            f"recursive={self.recursive}"
        )

        items = self._list_files(service, self.folder_id)

        if not items:
            print("[GDriveSource] No files found in the specified folder.")
            return []

        downloaded_files: List[str] = []

        for item in items:
            file_id = item["id"]
            file_name = item["name"]
            mime_type = item["mimeType"]

            # Handle native Google Docs formats
            if mime_type in _GDOC_EXPORT_MAP:
                export_mime, ext = _GDOC_EXPORT_MAP[mime_type]
                if not file_name.endswith(ext):
                    file_name += ext

                local_path = self.local_dir / file_name

                try:
                    request = service.files().export_media(
                        fileId=file_id, mimeType=export_mime
                    )
                    buf = io.BytesIO()
                    downloader = MediaIoBaseDownload(buf, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

                    with open(local_path, "wb") as f:
                        f.write(buf.getvalue())

                    downloaded_files.append(str(local_path))
                    print(f"[GDriveSource] Exported: {file_name} → {local_path}")

                except Exception as exc:
                    print(f"[GDriveSource] Error exporting '{file_name}': {exc}")

            else:
                # Binary file — direct download
                local_path = self.local_dir / file_name

                try:
                    request = service.files().get_media(fileId=file_id)
                    buf = io.BytesIO()
                    downloader = MediaIoBaseDownload(buf, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

                    with open(local_path, "wb") as f:
                        f.write(buf.getvalue())

                    downloaded_files.append(str(local_path))
                    print(f"[GDriveSource] Downloaded: {file_name} → {local_path}")

                except Exception as exc:
                    print(f"[GDriveSource] Error downloading '{file_name}': {exc}")

        print(f"[GDriveSource] Total downloaded: {len(downloaded_files)} file(s).")
        return downloaded_files
