"""
Amazon Bedrock Dense Embedder
Provider key : "bedrock"
Embedding type: dense
Modality     : text

Supported models:
    - amazon.titan-embed-text-v2:0     (1024-dim)
    - amazon.titan-embed-text-v1       (1536-dim, legacy)
    - cohere.embed-english-v3          (1024-dim)

Extra config fields:
    region   : "us-east-1"
    profile  : AWS profile name (optional)
"""

import json
from typing import List
from embedding.base import BaseEmbedder, EmbeddingConfig


class BedrockEmbedder(BaseEmbedder):
    """Dense text embedder backed by Amazon Bedrock."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 is required → pip install boto3"
            ) from exc

        session_kwargs = {}
        if config.extra.get("profile"):
            session_kwargs["profile_name"] = config.extra["profile"]

        session = boto3.Session(**session_kwargs)
        self._client = session.client(
            "bedrock-runtime",
            region_name=config.extra.get("region", "us-east-1"),
        )

    def _embed_titan(self, text: str) -> List[float]:
        payload = {
            "inputText": text,
            "dimensions": self.config.dimensions,
            "normalize": self.config.normalize,
        }
        response = self._client.invoke_model(
            modelId=self.config.model,
            body=json.dumps(payload),
            contentType="application/json",
        )
        body = json.loads(response["body"].read())
        return body["embedding"]

    def _embed_cohere(self, texts: List[str], input_type: str = "search_document") -> List[List[float]]:
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
        all_vectors: List[List[float]] = []

        is_cohere = self.config.model.startswith("cohere.")
        if is_cohere:
            for i in range(0, len(texts), self.config.batch_size):
                batch = texts[i : i + self.config.batch_size]
                all_vectors.extend(self._embed_cohere(batch))
        else:
            # Titan models are single-text per call
            for text in texts:
                all_vectors.append(self._embed_titan(text))

        return all_vectors
