from config.logger import setup_logger

logger = setup_logger(__name__)

import json

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class BedrockEmbedder(BaseEmbedder):
    """Dense text embedder backed by Amazon Bedrock."""

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("-------START Initializing BedrockEmbedder-----------")

        logger.debug(f"Bedrock model configured: {config.model}")

        logger.debug(f"Embedding dimensions: {config.dimensions}")

        logger.debug(f"AWS region: {config.extra.get('region', 'us-east-1')}")

        try:
            import boto3

        except ImportError as exc:

            logger.exception("boto3 import failed")

            raise ImportError("boto3 is required → pip install boto3") from exc

        session_kwargs = {}

        if config.extra.get("profile"):

            logger.debug(f"Using AWS profile: {config.extra['profile']}")

            session_kwargs["profile_name"] = config.extra["profile"]

        session = boto3.Session(**session_kwargs)

        self._client = session.client(
            "bedrock-runtime",
            region_name=config.extra.get("region", "us-east-1"),
        )

        logger.info("-------END Bedrock client initialized successfully---------------")

    def _embed_titan(self, text: str) -> List[float]:

        logger.debug(f"Generating Titan embedding for text length: {len(text)}")

        payload = {
            "inputText": text,
        }

        response = self._client.invoke_model(
            modelId=self.config.model,
            body=json.dumps(payload),
            contentType="application/json",
        )

        body = json.loads(response["body"].read())

        return body["embedding"]

    def _embed_cohere(
        self, texts: List[str], input_type: str = "search_document"
    ) -> List[List[float]]:

        logger.debug(
            f"Generating Cohere Bedrock embeddings for batch size: {len(texts)}"
        )

        payload = {
            "texts": texts,
            "input_type": input_type,
        }

        response = self._client.invoke_model(
            modelId=self.config.model,
            body=json.dumps(payload),
            contentType="application/json",
        )

        body = json.loads(response["body"].read())

        return body["embeddings"]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info(
                f"Starting Bedrock embedding generation for {len(texts)} text(s)"
            )

            all_vectors: List[List[float]] = []

            is_cohere = self.config.model.startswith("cohere.")

            logger.debug(f"Bedrock provider mode: {'cohere' if is_cohere else 'titan'}")

            if is_cohere:

                for i in range(0, len(texts), self.config.batch_size):

                    batch = texts[i : i + self.config.batch_size]

                    logger.debug(f"Processing Bedrock Cohere batch size: {len(batch)}")

                    all_vectors.extend(self._embed_cohere(batch))

            else:

                for text in texts:

                    all_vectors.append(self._embed_titan(text))

            logger.info("Bedrock embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("Bedrock embedding generation failed")

            raise
