from pathlib import Path
from typing import List
from source.base import DataSource
from source.utils import ensure_dir


class SharePointSource(DataSource):

    def __init__(self, config):
        self.site_url = config["source"]["site_url"]
        self.client_id = config["source"]["client_id"]
        self.client_secret = config["source"]["client_secret"]
        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)

    def download(self) -> List[str]:
        # Placeholder: Use Office365-REST-Python-Client or Microsoft Graph API
        print("Downloading from SharePoint...")
        return []
