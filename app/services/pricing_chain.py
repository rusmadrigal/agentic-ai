"""
LangChain RunnableSequence for pricing decisions.

Invoke with:
  chain.invoke({"product_json": str, "competitors_json": str, "rag_context": str})
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

_PRICING_SYSTEM = """You are a pricing strategy expert for e-commerce. Use the Context section when it contains retrieved knowledge; if Context is empty or whitespace, rely only on Product and Competitors.

You receive product JSON (list price as price_usd, stock when present) and competitor rows (title, price).

You MUST:
1. Compute the arithmetic mean of competitor prices (use only non-negative numeric prices; if there are no valid competitors, say so in reasoning and base the call on list price only).
2. Compare the product list price to that average. Compute the percentage gap: ((list_price - average) / average) * 100 when average > 0; interpret it in reasoning (positive = priced above market, negative = below).
3. Factor stock level into promotion and inventory_action (e.g. low stock vs excess inventory).
4. Pick exactly one pricing_strategy, one of these literal strings: increase_price, decrease_price, match_market.

Return ONLY valid JSON (no markdown, no text before or after the object) with exactly these keys:
{{
  "pricing_strategy": "increase_price" or "decrease_price" or "match_market",
  "recommended_price": <number>,
  "promotion": "concise promotion guidance",
  "inventory_action": "concise inventory / supply guidance",
  "reasoning": "2-4 sentences, business-focused; mention competitor average, gap %, and stock where relevant",
  "confidence": "low" or "medium" or "high"
}}

Be concise, realistic, and grounded in the numbers given. Return strict JSON only (no markdown, no prose outside the object)."""

_PRICING_HUMAN = """Product:
{product_json}

Competitors:
{competitors_json}

Context:
{rag_context}

Task: Using Product, Competitors, and Context (when useful), follow the system rules and output the single JSON object with pricing_strategy, recommended_price, promotion, inventory_action, reasoning, and confidence."""


def build_pricing_decision_chain(
    *,
    model: str,
    api_key: str,
    temperature: float = 0.3,
) -> Runnable:
    """Single RunnableSequence: ChatPromptTemplate | ChatOpenAI (strict JSON)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _PRICING_SYSTEM),
            ("human", _PRICING_HUMAN),
        ],
    )
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    return prompt | llm
