import json
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import ProductBrief, RetrievedChunk
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


def _product_query_text(brief: ProductBrief) -> str:
    p = brief.product
    parts = [
        p.title,
        p.description or "",
        p.category or "",
        " ".join(p.constraints),
    ]
    if brief.competitors:
        parts.append("competitors: " + " ".join(c.name for c in brief.competitors))
        parts.extend(c.positioning_notes for c in brief.competitors if c.positioning_notes)
    return "\n".join(x for x in parts if x).strip()


def load_vector_store_from_disk() -> VectorStore:
    index_path = settings.faiss_index_path
    meta_path = settings.faiss_meta_path
    if not index_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"FAISS artifacts missing at {index_path} / {meta_path}. "
            "Run: python scripts/build_index.py"
        )
    return VectorStore.load(index_path, meta_path)


class Retriever:
    def __init__(self, store: VectorStore, embedder: EmbeddingService) -> None:
        self._store = store
        self._embedder = embedder

    @classmethod
    def from_default_paths(cls) -> "Retriever":
        return cls(load_vector_store_from_disk(), EmbeddingService())

    async def retrieve(self, product: ProductBrief, k: int = 4) -> list[RetrievedChunk]:
        q = _product_query_text(product)
        qv = await self._embedder.embed_query(q)
        hits = self._store.search(qv, k=k)
        return [
            RetrievedChunk(id=hid, title=title, text=text, score=score)
            for hid, title, text, score in hits
        ]


def load_knowledge_chunks(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("knowledge_base.json must be a list of objects")
    return raw
