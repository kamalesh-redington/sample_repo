import json
import boto3


class S3ObjectStore:

    def __init__(self, config):

        cfg = config["object_store"]

        self.bucket = cfg["bucket"]

        self.prefix = cfg["prefix"]

        self.documents_path = cfg["layout"]["documents_path"]

        self.embeddings_path = cfg["layout"]["embeddings_path"]

        self.metadata_path = cfg["layout"]["metadata_path"]

        self.s3 = boto3.client("s3")

    def connect(self):

        return True

    def save_document(
        self,
        file_name: str,
        content: str
    ):

        key = (
            f"{self.prefix}"
            f"{self.documents_path}"
            f"{file_name}.txt"
        )

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content.encode("utf-8")
        )

    def save_embedding(
        self,
        key_name: str,
        embedding: dict
    ):

        key = (
            f"{self.prefix}"
            f"{self.embeddings_path}"
            f"{key_name}.json"
        )

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(embedding)
        )

    def save_metadata(
        self,
        key_name: str,
        metadata: dict
    ):

        key = (
            f"{self.prefix}"
            f"{self.metadata_path}"
            f"{key_name}.json"
        )

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(metadata)
        )