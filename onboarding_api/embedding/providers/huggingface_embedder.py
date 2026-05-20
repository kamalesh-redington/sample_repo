from config.logger import setup_logger

logger = setup_logger(__name__)

import os

from typing import List

from embedding.base import BaseEmbedder, EmbeddingConfig


class HuggingFaceEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing HuggingFaceEmbedder")

        self._use_local: bool = config.extra.get("use_local", False)

        logger.debug(f"HuggingFace local mode: {self._use_local}")

        logger.debug(f"HuggingFace model configured: {config.model}")

        if self._use_local:

            logger.info("Initializing local HuggingFace model")

            self._init_local(config)

        else:

            logger.info("Initializing HuggingFace inference API")

            self._init_api(config)

    def _init_local(self, config: EmbeddingConfig):

        try:

            from transformers import AutoModel, AutoTokenizer
            import torch

        except ImportError as exc:

            logger.exception("Transformers import failed")

            raise ImportError(
                "transformers + torch required → pip install transformers torch"
            ) from exc

        import torch
        from transformers import AutoModel, AutoTokenizer

        device = config.extra.get("device", "cpu")

        logger.debug(f"HuggingFace device configured: {device}")

        self._device = torch.device(device)

        self._tokenizer = AutoTokenizer.from_pretrained(config.model)

        self._model = AutoModel.from_pretrained(config.model).to(self._device)

        self._model.eval()

        logger.info("Local HuggingFace model loaded successfully")

    def _local_embed(self, texts: List[str]) -> List[List[float]]:

        import torch

        logger.info(f"Starting local HuggingFace embeddings for {len(texts)} text(s)")

        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):

            batch = texts[i : i + self.config.batch_size]

            logger.debug(f"Processing local HF batch size: {len(batch)}")

            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self._device)

            with torch.no_grad():

                output = self._model(**encoded)

            if self.config.pooling == "cls":

                vectors = output.last_hidden_state[:, 0, :]

            elif self.config.pooling == "max":

                vectors = output.last_hidden_state.max(dim=1).values

            else:

                attention_mask = encoded["attention_mask"].unsqueeze(-1).float()

                vectors = (output.last_hidden_state * attention_mask).sum(
                    1
                ) / attention_mask.sum(1)

            if self.config.normalize:

                vectors = torch.nn.functional.normalize(vectors, p=2, dim=-1)

            all_vectors.extend(vectors.cpu().tolist())

        logger.info("Local HuggingFace embeddings completed successfully")

        logger.debug(f"Generated vectors count: {len(all_vectors)}")

        return all_vectors

    def _init_api(self, config: EmbeddingConfig):

        try:

            from huggingface_hub import InferenceClient

        except ImportError as exc:

            logger.exception("huggingface_hub import failed")

            raise ImportError(
                "huggingface_hub required → pip install huggingface-hub"
            ) from exc

        token = config.extra.get("api_key") or os.environ.get("HUGGINGFACE_API_KEY")

        from huggingface_hub import InferenceClient

        self._api_client = InferenceClient(model=config.model, token=token)

        logger.info("HuggingFace API client initialized successfully")

    def _api_embed(self, texts: List[str]) -> List[List[float]]:

        logger.info(f"Starting HuggingFace API embeddings for {len(texts)} text(s)")

        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):

            batch = texts[i : i + self.config.batch_size]

            logger.debug(f"Processing HF API batch size: {len(batch)}")

            result = self._api_client.feature_extraction(batch)

            import numpy as np

            arr = np.array(result)

            if arr.ndim == 3:
                arr = arr.mean(axis=1)

            all_vectors.extend(arr.tolist())

        logger.info("HuggingFace API embeddings completed successfully")

        logger.debug(f"Generated vectors count: {len(all_vectors)}")

        return all_vectors

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            logger.info("Starting HuggingFace embedding pipeline")

            if self._use_local:
                return self._local_embed(texts)

            return self._api_embed(texts)

        except Exception as e:

            logger.exception("HuggingFace embedding generation failed")

            raise
