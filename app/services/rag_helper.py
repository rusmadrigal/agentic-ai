"""
RAG helpers for pricing decisions. Retriever is registered at app startup (see api lifespan).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.rag.retriever import Retriever

logger = get_logger(__name__)

_pricing_retriever: Optional["Retriever"] = None


def set_pricing_retriever(retriever: Optional["Retriever"]) -> None:
    """Called from FastAPI lifespan when FAISS + Retriever are ready (or None on shutdown)."""
    global _pricing_retriever
    _pricing_retriever = retriever


def get_pricing_retriever() -> Optional["Retriever"]:
    return _pricing_retriever


def _build_rag_query(product: dict[str, Any], competitors: list[dict[str, Any]]) -> str:
    title = str(product.get("title") or "").strip()
    price = product.get("price_usd")
    parts: list[str] = []
    if title:
        parts.append(title)
    if price is not None:
        parts.append(f"list price {price}")
    peer_bits: list[str] = []
    for c in competitors:
        label = str(c.get("title") or c.get("name") or "").strip()
        p = c.get("price")
        if p is not None:
            peer_bits.append(f"{label} {p}".strip() if label else str(p))
    if peer_bits:
        parts.append("competitor prices: " + ", ".join(peer_bits))
    return " ".join(parts).strip()


def retrieve_context(
    retriever: Optional["Retriever"],
    product: dict[str, Any],
    competitors: list[dict[str, Any]],
) -> str:
    if retriever is None:
        return ""
    query = _build_rag_query(product, competitors)
    if not query:
        return ""
    try:
        docs = retriever.get_relevant_documents(query, k=4)
    except Exception as exc:
        logger.warning("RAG retrieve_context failed: %s", exc)
        return ""
    if not docs:
        return ""
    return "\n\n".join(docs[:4])
