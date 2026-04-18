import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VectorStore:
    index: faiss.IndexFlatL2
    ids: list[str]
    titles: list[str]
    texts: list[str]
    dim: int

    @classmethod
    def from_embeddings(
        cls,
        embeddings: np.ndarray,
        ids: list[str],
        titles: list[str],
        texts: list[str],
    ) -> "VectorStore":
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be 2D")
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings.astype(np.float32))
        return cls(index=index, ids=ids, titles=titles, texts=texts, dim=dim)

    def search(self, query_vec: np.ndarray, k: int = 4) -> list[tuple[str, str, str, float]]:
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)
        distances, idxs = self.index.search(query_vec.astype(np.float32), k)
        out: list[tuple[str, str, str, float]] = []
        for rank, j in enumerate(idxs[0]):
            if j < 0 or j >= len(self.ids):
                continue
            dist = float(distances[0][rank])
            score = 1.0 / (1.0 + dist)
            out.append((self.ids[j], self.titles[j], self.texts[j], score))
        return out

    def save(self, index_path: Path, meta_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_path))
        meta = {"ids": self.ids, "titles": self.titles, "texts": self.texts, "dim": self.dim}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("saved FAISS index to %s", index_path)

    @classmethod
    def load(cls, index_path: Path, meta_path: Path) -> "VectorStore":
        index = faiss.read_index(str(index_path))
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return cls(
            index=index,
            ids=list(meta["ids"]),
            titles=list(meta["titles"]),
            texts=list(meta["texts"]),
            dim=int(meta["dim"]),
        )
