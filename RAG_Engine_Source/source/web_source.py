import requests
from pathlib import Path
from typing import List
from source.base import DataSource
from source.utils import ensure_dir


class WebSource(DataSource):

    def __init__(self, config):
        self.urls = config["source"]["urls"]
        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)

    def download(self) -> List[str]:
        downloaded_files = []

        for url in self.urls:
            filename = url.split("/")[-1]
            local_path = self.local_dir / filename

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(response.content)

                downloaded_files.append(str(local_path))
                print(f"Downloaded: {url}")

            except Exception as e:
                print(f"Error downloading {url}: {e}")

        return downloaded_files
