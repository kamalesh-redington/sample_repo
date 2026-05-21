from config.logger import setup_logger

logger = setup_logger(__name__)

from typing import Dict, List

from embedding.base import BaseEmbedder, EmbeddingConfig


class SpladeEmbedder(BaseEmbedder):

    def __init__(self, config: EmbeddingConfig):

        super().__init__(config)

        logger.info("Initializing SPLADEEmbedder")

        logger.debug(f"SPLADE model configured: {config.model}")

        try:

            from transformers import AutoModelForMaskedLM, AutoTokenizer

            import torch

        except ImportError as exc:

            logger.exception("transformers import failed")

            raise ImportError(
                "transformers + torch required → pip install transformers torch"
            ) from exc

        import torch
        from transformers import AutoModelForMaskedLM, AutoTokenizer

        self._device = torch.device(config.extra.get("device", "cpu"))

        self._tokenizer = AutoTokenizer.from_pretrained(config.model)

        self._model = AutoModelForMaskedLM.from_pretrained(config.model).to(
            self._device
        )

        self._model.eval()

        logger.info("SPLADE model initialized successfully")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        try:

            import torch

            logger.info(f"Starting SPLADE embeddings for {len(texts)} text(s)")

            all_vectors = []

            for i in range(0, len(texts), self.config.batch_size):

                batch = texts[i : i + self.config.batch_size]

                logger.debug(f"Processing SPLADE batch size: {len(batch)}")

                encoded = self._tokenizer(
                    batch, padding=True, truncation=True, return_tensors="pt"
                ).to(self._device)

                with torch.no_grad():

                    outputs = self._model(**encoded)

                    logits = outputs.logits

                    sparse_vec = torch.max(
                        torch.log1p(torch.relu(logits)), dim=1
                    ).values

                all_vectors.extend(sparse_vec.cpu().tolist())

            logger.info("SPLADE embedding generation completed successfully")

            logger.debug(f"Generated vectors count: {len(all_vectors)}")

            return all_vectors

        except Exception as e:

            logger.exception("SPLADE embedding generation failed")

            raise
