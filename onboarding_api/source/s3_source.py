from config.logger import setup_logger

logger = setup_logger(__name__)

import boto3

from botocore.exceptions import ClientError

from pathlib import Path
from typing import List

from source.base import DataSource
from source.utils import ensure_dir


class S3Source(DataSource):

    def __init__(self, config):

        logger.info("Initializing S3 source")

        self.bucket = config["source"]["bucket"]

        self.prefix = config["source"].get("prefix", "")

        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)

        logger.debug(f"S3 bucket configured: {self.bucket}")

        logger.debug(f"S3 prefix configured: {self.prefix}")

        self.s3 = boto3.client("s3")

        logger.info("S3 client initialized successfully")

    def download(self) -> List[str]:

        try:

            logger.info("Starting S3 file download process")

            downloaded_files = []

            paginator = self.s3.get_paginator("list_objects_v2")

            pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)

            logger.debug("S3 paginator initialized")

            for page in pages:

                logger.debug("Processing S3 page response")

                for obj in page.get("Contents", []):

                    key = obj["Key"]

                    logger.debug(f"Processing S3 object key: {key}")

                    if key.endswith("/"):

                        logger.debug(f"Skipping directory marker: {key}")

                        continue

                    local_path = self.local_dir / Path(key).name

                    try:

                        logger.info(f"Downloading S3 object: {key}")

                        self.s3.download_file(self.bucket, key, str(local_path))

                        downloaded_files.append(str(local_path))

                        logger.info(f"S3 file downloaded successfully: {local_path}")

                    except ClientError as exc:

                        logger.exception(f"S3 download failed for object: {key}")

            logger.info(f"Total S3 files downloaded: {len(downloaded_files)}")

            return downloaded_files

        except Exception as e:

            logger.exception("S3 download pipeline failed")

            raise
