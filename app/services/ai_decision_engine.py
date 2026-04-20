"""
LLM-powered pricing decision layer (LangChain + OpenAI).

Ingestion (DummyJSON / manual) stays in the API route; this module only turns
structured product + competitor rows into a validated decisions block.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.pricing_chain import build_pricing_decision_chain
from app.services.rag_helper import get_pricing_retriever, retrieve_context

logger = get_logger(__name__)


def _message_content_to_str(content: Any) -> str:
    """Normalize AIMessage.content (str or multimodal blocks) to a single string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts).strip()
    return str(content).strip()


def generate_ai_decision(product: dict[str, Any], competitors: list[dict[str, Any]]) -> str:
    """Run the shared pricing RunnableSequence; return JSON string for parse_ai_response."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    product_json = json.dumps(product, indent=2, ensure_ascii=False)
    competitors_json = json.dumps(competitors, indent=2, ensure_ascii=False)
    rag_context = retrieve_context(get_pricing_retriever(), product, competitors)

    chain = build_pricing_decision_chain(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    message = chain.invoke(
        {
            "product_json": product_json,
            "competitors_json": competitors_json,
            "rag_context": rag_context,
        },
    )
    return _message_content_to_str(message.content)


def _extract_json_object(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        return fence.group(1).strip()
    return text


def parse_ai_response(raw: str, *, fallback_price: float) -> dict[str, Any]:
    """Parse model output into a dict suitable for SimulatedDecisionsBlock (+ confidence)."""
    text = _extract_json_object(raw)
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("expected JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM output not valid JSON object: %s", exc)
        return {
            "pricing_strategy": "fallback_parse_error",
            "recommended_price": float(fallback_price),
            "promotion": "Manual review recommended: model output was not valid JSON.",
            "inventory_action": "Hold pricing changes until inputs and model output are validated.",
            "reasoning": (raw.strip()[:2000] if raw.strip() else "No parseable JSON returned."),
            "confidence": "low",
        }

    try:
        rec = float(data.get("recommended_price", fallback_price))
    except (TypeError, ValueError):
        rec = float(fallback_price)

    conf = data.get("confidence")
    if conf not in ("low", "medium", "high", None):
        conf = "medium"

    return {
        "pricing_strategy": str(data.get("pricing_strategy") or "unspecified").strip() or "unspecified",
        "recommended_price": rec,
        "promotion": str(data.get("promotion") or "").strip() or "See reasoning and refine with merchandising.",
        "inventory_action": str(data.get("inventory_action") or "").strip()
        or "Align stock with the pricing scenario after leadership review.",
        "reasoning": str(data.get("reasoning") or "").strip() or "No reasoning provided by model.",
        "confidence": conf,
    }
