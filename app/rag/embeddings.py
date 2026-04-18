import hashlib
from typing import Optional

import numpy as np
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EMBED_DIM = 1536


def _stable_seed(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def pseudo_embedding(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    rng = np.random.default_rng(_stable_seed(text))
    vec = rng.normal(size=dim).astype(np.float32)
    norm = np.linalg.norm(vec) or 1.0
    return (vec / norm).astype(np.float32)


class EmbeddingService:
    def __init__(self) -> None:
        self._mode = settings.embedding_mode.lower().strip()
        self._client: Optional[AsyncOpenAI] = None
        if settings.openai_api_key and self._mode != "pseudo":
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, EMBED_DIM), dtype=np.float32)

        if self._client is None or self._mode == "pseudo":
            logger.info("embeddings: using pseudo vectors (no OpenAI client)")
            return np.stack([pseudo_embedding(t) for t in texts], axis=0).astype(np.float32)

        response = await self._client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
            dimensions=EMBED_DIM,
        )
        vectors = [np.array(d.embedding, dtype=np.float32) for d in response.data]
        mat = np.stack(vectors, axis=0)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (mat / norms).astype(np.float32)

    async def embed_query(self, text: str) -> np.ndarray:
        mat = await self.embed_texts([text])
        return mat[0]
