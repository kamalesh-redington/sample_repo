from config.logger import setup_logger

logger = setup_logger(__name__)

import requests

from pathlib import Path
from typing import List

from source.base import DataSource
from source.utils import ensure_dir


class WebSource(DataSource):

    def __init__(self, config):

        logger.info("Initializing WebSource")

        self.urls = config["source"]["urls"]

        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)

        logger.debug(f"Configured URLs count: {len(self.urls)}")

    def download(self) -> List[str]:

        try:

            logger.info("Starting web file download process")

            downloaded_files = []

            for url in self.urls:

                logger.info(f"Downloading URL: {url}")

                filename = url.split("/")[-1]

                local_path = self.local_dir / filename

                try:

                    response = requests.get(url, timeout=30)

                    response.raise_for_status()

                    logger.debug(f"HTTP response received: {response.status_code}")

                    with open(local_path, "wb") as f:

                        f.write(response.content)

                    downloaded_files.append(str(local_path))

                    logger.info(f"Web file downloaded successfully: {local_path}")

                except Exception as e:

                    logger.exception(f"Failed downloading URL: {url}")

            logger.info(f"Total web files downloaded: {len(downloaded_files)}")

            return downloaded_files

        except Exception as e:

            logger.exception("Web download pipeline failed")

            raise
