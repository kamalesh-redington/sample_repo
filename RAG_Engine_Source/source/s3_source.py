import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import List
from source.base import DataSource
from source.utils import ensure_dir


class S3Source(DataSource):

    def __init__(self, config):
        self.bucket = config["source"]["bucket"]
        self.prefix = config["source"].get("prefix", "")
        self.local_dir = Path(config.get("local", {}).get("data_dir", "./data"))

        ensure_dir(self.local_dir)
        self.s3 = boto3.client("s3")

    def download(self) -> List[str]:
        downloaded_files = []

        paginator = self.s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)
        print(pages)
        for page in pages:
            for obj in page.get("Contents", []):
                key = "CROWDSTRIKE/CROWDSTRIKE/Product_Docs/SSG/Security/PA_RED_COPILOT_AI_PLATFORM/Cortex SecOps/XDR/cortex-xdr.pdf"
                print(key)
                if key.endswith("/"):
                    continue

                local_path = self.local_dir / Path(key).name

                try:
                    self.s3.download_file(self.bucket, key, str(local_path))
                    downloaded_files.append(str(local_path))
                    print(f"Downloaded: {key}")
                    return [str(local_path)]

                except ClientError as exc:
                    print(f"Error downloading {key}: {exc}")

        return downloaded_files
