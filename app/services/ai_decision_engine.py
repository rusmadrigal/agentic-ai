"""
LLM-powered pricing decision layer (OpenAI).

Ingestion (DummyJSON / manual) stays in the API route; this module only turns
structured product + competitor rows into a validated decisions block.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _product_and_competitors_prompt(product: dict[str, Any], competitors: list[dict[str, Any]]) -> str:
    return f"""You are a senior pricing strategist for an e-commerce company.

Analyze the product and competitor pricing, then return a structured decision.

Product (JSON):
{json.dumps(product, indent=2, ensure_ascii=False)}

Competitors (JSON array of {{title, price}}):
{json.dumps(competitors, indent=2, ensure_ascii=False)}

Return ONLY valid JSON with exactly this structure (no markdown, no prose):
{{
  "pricing_strategy": "short snake_case or phrase describing the strategy",
  "recommended_price": <number>,
  "promotion": "concise promotion guidance",
  "inventory_action": "concise inventory / supply guidance",
  "reasoning": "2-4 sentences, business-focused, non-technical",
  "confidence": "low" | "medium" | "high"
}}

Be concise, realistic, and grounded in the numbers given."""


def generate_ai_decision(product: dict[str, Any], competitors: list[dict[str, Any]]) -> str:
    """Call OpenAI chat completions; return message content (JSON string)."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[{"role": "user", "content": _product_and_competitors_prompt(product, competitors)}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return (content or "").strip()


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
