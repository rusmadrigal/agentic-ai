from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Competitor(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    price_usd: Optional[float] = Field(default=None, ge=0)
    positioning_notes: str = Field(default="", max_length=2000)
    url: Optional[str] = Field(default=None, max_length=500)


class Product(BaseModel):
    sku: Optional[str] = Field(default=None, description="Stock keeping unit or internal id")
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)
    category: Optional[str] = Field(default=None, max_length=200)
    price_usd: float = Field(..., ge=0)
    cost_usd: Optional[float] = Field(default=None, ge=0)
    inventory_units: Optional[int] = Field(default=None, ge=0)
    margin_target_pct: Optional[float] = Field(default=None, ge=0, le=100)
    constraints: List[str] = Field(default_factory=list, max_length=20)


_PRODUCT_BRIEF_OPENAPI_EXAMPLE: dict = {
    "product": {
        "sku": "SKU-4412",
        "title": "Merino crewneck sweater, limited colors",
        "description": "Mid-weight merino blend; strong email repeats; sizing content is thin.",
        "category": "Apparel / Knitwear",
        "price_usd": 89.0,
        "cost_usd": 38.0,
        "inventory_units": 4200,
        "margin_target_pct": 52.0,
        "constraints": ["Avoid sitewide 20% coupons", "Premium adjacency"],
    },
    "competitors": [
        {
            "name": "Nordic Knit Co. Crew",
            "price_usd": 78.0,
            "positioning_notes": "Frequent promos; stronger sizing content.",
        }
    ],
}


class ProductBrief(BaseModel):
    """Root POST body: product + optional competitors (no extra wrapper)."""

    model_config = ConfigDict(json_schema_extra={"example": _PRODUCT_BRIEF_OPENAPI_EXAMPLE})

    product: Product
    competitors: List[Competitor] = Field(default_factory=list, max_length=30)


class RetrievedChunk(BaseModel):
    id: str
    title: str
    text: str
    score: float


class AnalyzerOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    market_signals: List[str] = Field(default_factory=list, max_length=24)
    risks: List[str] = Field(default_factory=list, max_length=24)
    opportunities: List[str] = Field(default_factory=list, max_length=24)
    competitive_notes: List[str] = Field(default_factory=list, max_length=24)
    key_metrics_to_watch: List[str] = Field(default_factory=list, max_length=24)

    @field_validator(
        "market_signals",
        "risks",
        "opportunities",
        "competitive_notes",
        "key_metrics_to_watch",
        mode="before",
    )
    @classmethod
    def _coerce_str_lists(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            out: List[str] = []
            for x in v[:24]:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    out.append(s)
            return out
        return v


class DecisionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision: str
    rationale: str
    confidence: Literal["low", "medium", "high"]
    owner: str = Field(..., description="Suggested owning function, e.g. Merchandising")
    horizon_days: int = Field(..., ge=1, le=365)
    success_metric: str

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v: Any) -> Any:
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("low", "medium", "high"):
                return s
        return v

    @field_validator("horizon_days", mode="before")
    @classmethod
    def _coerce_horizon_days(cls, v: Any) -> Any:
        if isinstance(v, bool):
            return v
        if isinstance(v, float):
            return int(round(v))
        if isinstance(v, str) and v.strip().isdigit():
            return int(v.strip())
        return v


class DecisionMakerOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pricing: Optional[DecisionItem] = None
    promotion: Optional[DecisionItem] = None
    inventory_ops: Optional[DecisionItem] = None
    catalog_positioning: Optional[DecisionItem] = None
    customer_experience: Optional[DecisionItem] = None


class ExecutiveSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: str
    situation: str
    recommendation: str
    next_steps: List[str] = Field(default_factory=list, max_length=12)

    @field_validator("next_steps", mode="before")
    @classmethod
    def _coerce_next_steps(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v


class FormatterEnvelope(BaseModel):
    """LLM sometimes wraps the memo; accept both shapes in one parse."""

    model_config = ConfigDict(extra="ignore")

    headline: Optional[str] = None
    situation: Optional[str] = None
    recommendation: Optional[str] = None
    next_steps: Optional[List[str]] = None
    executive_summary: Optional[ExecutiveSummary] = None

    def to_executive_summary(self) -> ExecutiveSummary:
        if self.executive_summary is not None:
            return self.executive_summary
        if self.headline is not None and self.situation is not None and self.recommendation is not None:
            return ExecutiveSummary(
                headline=self.headline,
                situation=self.situation,
                recommendation=self.recommendation,
                next_steps=self.next_steps or [],
            )
        raise ValueError("formatter payload missing executive fields")


class ClientDeliverable(BaseModel):
    executive_summary: ExecutiveSummary
    analysis: AnalyzerOutput
    decisions: DecisionMakerOutput
    appendix: dict[str, Any] = Field(default_factory=dict)


class DecisionEngineResponse(BaseModel):
    product: ProductBrief
    retrieval: List[RetrievedChunk]
    deliverable: ClientDeliverable
    workflow_version: str = "mvp-1.0"
