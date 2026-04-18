"""
Build FAISS index from `data/knowledge_base.json`.

Uses the same embedding configuration as the API (`EMBEDDING_MODE`, OpenAI models).
Run from repository root:

    python scripts/build_index.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import load_knowledge_chunks
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


async def main() -> None:
    configure_logging()
    mode = settings.embedding_mode.lower().strip()
    if mode != "pseudo" and not settings.openai_api_key:
        logger.warning(
            "OPENAI_API_KEY is unset: building the FAISS index with pseudo embeddings. "
            "If you add a key later only at runtime, retrieval quality will be wrong until you "
            "redeploy (or set EMBEDDING_MODE=pseudo for a consistent offline index)."
        )
    kb_path = settings.knowledge_base_path
    chunks = load_knowledge_chunks(kb_path)
    texts: list[str] = []
    ids: list[str] = []
    titles: list[str] = []
    bodies: list[str] = []
    for row in chunks:
        ids.append(str(row["id"]))
        titles.append(str(row["title"]))
        body = str(row["text"])
        bodies.append(body)
        texts.append(f"{row['title']}\n{body}")

    embedder = EmbeddingService()
    vectors = await embedder.embed_texts(texts)
    store = VectorStore.from_embeddings(vectors, ids, titles, bodies)
    store.save(settings.faiss_index_path, settings.faiss_meta_path)
    logger.info("indexed %s chunks into %s", len(ids), settings.faiss_index_path)


if __name__ == "__main__":
    asyncio.run(main())
