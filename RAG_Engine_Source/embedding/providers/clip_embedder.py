"""
CLIP Multimodal Embedder (Image + Text)
Provider key  : "clip"
Embedding type: dense
Modality      : multimodal  (text | image | text+image)

Models:
    - openai/clip-vit-base-patch32       (512-dim)
    - openai/clip-vit-large-patch14      (768-dim)
    - laion/CLIP-ViT-H-14-laion2B-s32B-b79K (1024-dim, strongest)

Extra config fields:
    device     : "cpu" | "cuda" | "mps"
    image_size : 224  (default, matches most CLIP variants)
"""

from pathlib import Path
from typing import List, Union

from embedding.base import BaseEmbedder, EmbeddingConfig


class CLIPEmbedder(BaseEmbedder):
    """
    CLIP-based multimodal embedder.

    - embed_texts()   → text embeddings
    - embed_images()  → image embeddings (from file paths or PIL Images)
    - embed_mixed()   → combined fused vector (text + image mean)
    """

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise ImportError(
                "transformers required → pip install transformers"
            ) from exc

        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._device = torch.device(config.extra.get("device", "cpu"))
        self._processor = CLIPProcessor.from_pretrained(config.model)
        self._model = CLIPModel.from_pretrained(config.model).to(self._device)
        self._model.eval()
        self._torch = torch

    def _load_image(self, source: Union[str, Path]):
        """Load image from path or return PIL Image directly."""
        from PIL import Image
        if isinstance(source, (str, Path)):
            return Image.open(source).convert("RGB")
        return source  # assume PIL Image

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        import torch

        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            inputs = self._processor(
                text=batch, return_tensors="pt", padding=True, truncation=True
            ).to(self._device)

            with torch.no_grad():
                features = self._model.get_text_features(**inputs)

            if self.config.normalize:
                features = torch.nn.functional.normalize(features, p=2, dim=-1)

            all_vectors.extend(features.cpu().tolist())

        return all_vectors

    def embed_images(self, image_sources: List[Union[str, Path]]) -> List[List[float]]:
        """Embed images from file paths or PIL Images."""
        import torch

        all_vectors: List[List[float]] = []

        for i in range(0, len(image_sources), self.config.batch_size):
            batch_src = image_sources[i : i + self.config.batch_size]
            images = [self._load_image(src) for src in batch_src]
            inputs = self._processor(images=images, return_tensors="pt").to(self._device)

            with torch.no_grad():
                features = self._model.get_image_features(**inputs)

            if self.config.normalize:
                features = torch.nn.functional.normalize(features, p=2, dim=-1)

            all_vectors.extend(features.cpu().tolist())

        return all_vectors

    def embed_mixed(
        self,
        texts: List[str],
        image_sources: List[Union[str, Path]],
    ) -> List[List[float]]:
        """
        Fuse text + image into a single vector per pair (element-wise mean).
        Both lists must be the same length.
        """
        import torch

        text_vecs = self._torch.tensor(self.embed_texts(texts))
        image_vecs = self._torch.tensor(self.embed_images(image_sources))
        fused = (text_vecs + image_vecs) / 2.0

        if self.config.normalize:
            fused = torch.nn.functional.normalize(fused, p=2, dim=-1)

        return fused.tolist()
