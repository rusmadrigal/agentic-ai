from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.schemas import Product

_EXAMPLE: dict = {
    "product_id": 1,
    "competitors": [
        {"title": "Brand A", "price": 100},
        {"title": "Brand B", "price": 130},
    ],
    "use_llm": True,
}


class CompetitorPriceInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., ge=0)


class SimulatedDecisionRequest(BaseModel):
    """Either `product_id` (DummyJSON) or a manual `product` snapshot, not both."""

    model_config = ConfigDict(json_schema_extra={"example": _EXAMPLE})

    product_id: Optional[int] = Field(default=None, ge=1)
    product: Optional[Product] = None
    competitors: list[CompetitorPriceInput] = Field(default_factory=list, max_length=30)
    use_llm: Optional[bool] = Field(
        default=None,
        description=(
            "If true, require OpenAI (set OPENAI_API_KEY). If false, use rule-based logic. "
            "If omitted, use LLM when an API key is configured, otherwise simulated."
        ),
    )

    @model_validator(mode="after")
    def xor_product_source(self) -> SimulatedDecisionRequest:
        if self.product_id is not None and self.product is not None:
            raise ValueError("Provide either product_id or product, not both.")
        if self.product_id is None and self.product is None:
            raise ValueError("Provide product_id (DummyJSON) or a manual product object.")
        return self


class SimulatedDecisionsBlock(BaseModel):
    pricing_strategy: str
    recommended_price: float
    promotion: str
    inventory_action: str
    reasoning: str
    confidence: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="Set when decisions come from the LLM; omitted for rule-based output.",
    )


class SimulatedDecisionResponse(BaseModel):
    product: dict[str, Any]
    competitors: list[dict[str, Any]]
    decisions: SimulatedDecisionsBlock
    source: Literal["dummyjson API", "manual"]
    decision_engine: Literal["llm", "simulated"]
