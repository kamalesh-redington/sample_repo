from config.logger import setup_logger

logger = setup_logger(__name__)

from pathlib import Path
from typing import List

from source.base import DataSource


class LocalFileSource(DataSource):

    def __init__(self, config):

        logger.info("Initializing LocalFileSource")

        self.path = Path(config["source"]["path"])

        logger.debug(f"Local source path configured: {self.path}")

    def download(self) -> List[str]:

        try:

            logger.info("Starting local file discovery")

            files = []

            if self.path.is_file():

                logger.info(f"Single local file detected: {self.path}")

                return [str(self.path)]

            logger.debug(f"Scanning directory recursively: {self.path}")

            for file in self.path.glob("**/*"):

                if file.is_file():

                    logger.debug(f"Local file discovered: {file}")

                    files.append(str(file))

            logger.info(f"Total local files discovered: {len(files)}")

            return files

        except Exception as e:

            logger.exception("Local file discovery failed")

            raise
