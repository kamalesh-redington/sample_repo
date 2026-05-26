import json
import boto3


class S3ObjectStore:

    def __init__(self, config: dict):

        cfg = config["object_store"]

        self.bucket = cfg["bucket"]

        self.region = cfg.get("region")

        self.s3 = boto3.client(
            "s3",
            region_name=self.region
        )

    # =========================================================
    # VALIDATE CONNECTION
    # =========================================================

    def connect(self):

        try:

            self.s3.head_bucket(
                Bucket=self.bucket
            )

            print(
                f"S3 connection successful | bucket={self.bucket}"
            )

            return True

        except Exception as e:

            raise RuntimeError(
                f"Failed connecting to S3 bucket: {e}"
            )

    # =========================================================
    # GENERIC JSON UPLOAD
    # =========================================================

    def upload_json(
        self,
        key: str,
        data: dict
    ):

        try:

            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(
                    data,
                    ensure_ascii=False
                ).encode("utf-8"),
                ContentType="application/json"
            )

        except Exception as e:

            raise RuntimeError(
                f"Failed uploading object to S3 | "
                f"key={key} | error={e}"
            )

    # =========================================================
    # STORE CHUNK
    # =========================================================

    def save_chunk(
        self,
        document_id: str,
        chunk_id: str,
        data: dict
    ):

        key = (
            f"chunks/"
            f"{document_id}/"
            f"{chunk_id}.json"
        )

        self.upload_json(
            key=key,
            data=data
        )

    # =========================================================
    # STORE EMBEDDING
    # =========================================================

    def save_embedding(
        self,
        document_id: str,
        chunk_id: str,
        data: dict
    ):

        key = (
            f"embeddings/"
            f"{document_id}/"
            f"{chunk_id}.json"
        )

        self.upload_json(
            key=key,
            data=data
        )

    # =========================================================
    # STORE METADATA
    # =========================================================

    def save_metadata(
        self,
        document_id: str,
        chunk_id: str,
        data: dict
    ):

        key = (
            f"metadata/"
            f"{document_id}/"
            f"{chunk_id}.json"
        )

        self.upload_json(
            key=key,
            data=data
        )