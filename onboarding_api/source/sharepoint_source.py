from config.logger import setup_logger

logger = setup_logger(__name__)

from pathlib import Path
from typing import List

from source.base import DataSource
from source.utils import ensure_dir


class SharePointSource(DataSource):

    def __init__(self, config):
        logger.info("Initializing SharePoint source")
        self.site_url = config["source"]["site_url"]
        self.client_id = config["source"]["client_id"]
        self.client_secret = config["source"]["client_secret"]
        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))
        ensure_dir(self.local_dir)
        logger.debug(f"SharePoint site URL configured: {self.site_url}")

    def download(self) -> List[str]:
        try:
            logger.info("Starting SharePoint download process")
            logger.warning("SharePoint download implementation is placeholder only")
            return []

        except Exception as e:

            logger.exception("SharePoint download failed")
            raise
