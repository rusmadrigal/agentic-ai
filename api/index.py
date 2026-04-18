import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.integrations.dummyjson import fetch_product_from_api, normalize_dummyjson_product
from app.models.schemas import Product
from app.models.simulated import SimulatedDecisionRequest, SimulatedDecisionResponse
from app.rag.retriever import Retriever
from app.services.orchestrator import DecisionOrchestrator
from app.services.rule_decisions import compute_simulated_decisions

configure_logging()
logger = get_logger(__name__)

_orchestrator: Optional[DecisionOrchestrator] = None

_DEMO_HTML_PATH = _ROOT / "app" / "static" / "demo.html"

_DESCRIPTION = """
**Decision flow:** ingest product context (DummyJSON or manual) → **simulated** pricing / promotion / inventory rules (MVP).

Optional **RAG + OpenAI agents** remain in the codebase for extension; this demo highlights external data and structured business output.

Open **`/`** for the interactive workflow, or **POST /v1/decisions** with `product_id` or `product` + competitor prices.
""".strip()

_TAGS_METADATA = [
    {
        "name": "demo",
        "description": "Human-friendly entry points for reviewers.",
    },
    {
        "name": "decisions",
        "description": "Simulated commercial decisions (pricing, promo, inventory).",
    },
    {
        "name": "ops",
        "description": "Health and readiness for deploy hooks.",
    },
    {
        "name": "external",
        "description": "External catalog data (DummyJSON).",
    },
]


def _manual_product_snapshot(p: Product) -> dict[str, Any]:
    return {
        "id": None,
        "title": p.title,
        "description": p.description,
        "category": p.category or "",
        "brand": "",
        "price_usd": float(p.price_usd),
        "stock": p.inventory_units,
        "sku": p.sku,
        "thumbnail": None,
        "rating": None,
        "constraints": p.constraints,
        "cost_usd": p.cost_usd,
        "margin_target_pct": p.margin_target_pct,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    configure_logging()
    if settings.openai_api_key:
        logger.info("OPENAI_API_KEY is configured (optional for simulated /v1/decisions)")
    else:
        logger.warning(
            "OPENAI_API_KEY is not set; optional for LLM extensions. Simulated decisions do not require it.",
        )
    try:
        retriever = Retriever.from_default_paths()
        _orchestrator = DecisionOrchestrator(retriever)
        logger.info("orchestrator initialized (FAISS index loaded)")
    except FileNotFoundError as exc:
        logger.warning("startup: %s", exc)
        _orchestrator = None
    yield
    _orchestrator = None


app = FastAPI(
    title="Agentic AI Decision Engine for E-commerce",
    description=_DESCRIPTION,
    version="0.2.0",
    lifespan=lifespan,
    openapi_tags=_TAGS_METADATA,
    contact={"name": "Portfolio / take-home submission"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, tags=["demo"])
async def root() -> HTMLResponse:
    """Interactive demo for hiring-manager / panel review (no separate frontend build)."""
    if _DEMO_HTML_PATH.is_file():
        return HTMLResponse(_DEMO_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<p>Demo UI missing. Add <code>app/static/demo.html</code>.</p>"
        "<p><a href='/docs'>OpenAPI docs</a></p>",
        status_code=200,
    )


@app.get("/api/external-products/{product_id}", tags=["external"])
async def get_external_product(product_id: int) -> dict[str, Any]:
    """Fetch and normalize a product from DummyJSON (for the demo “Fetch product” step)."""
    raw = await run_in_threadpool(fetch_product_from_api, product_id)
    return normalize_dummyjson_product(raw)


@app.get("/api/readiness", tags=["ops"])
async def readiness() -> dict:
    """Signals for UI banners and load balancers (no secrets)."""
    return {
        "openai_configured": bool(settings.openai_api_key),
        "rag_ready": _orchestrator is not None,
        "embedding_mode": settings.embedding_mode,
        "simulated_decisions_ready": True,
    }


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {
        "status": "ok",
        "rag_ready": _orchestrator is not None,
        "embedding_mode": settings.embedding_mode,
    }


@app.post(
    "/v1/decisions",
    response_model=SimulatedDecisionResponse,
    tags=["decisions"],
    summary="Generate simulated commercial decisions",
    response_description="Product context, competitor list, and rule-based pricing / promo / inventory actions.",
)
async def create_decision(payload: SimulatedDecisionRequest) -> SimulatedDecisionResponse:
    """
    Provide **`product_id`** to pull live data from DummyJSON, or a manual **`product`** object.
    Competitors use **`title`** + **`price`** (USD). No OpenAI key required for this endpoint.
    """
    comp_tuples = [(c.title, float(c.price)) for c in payload.competitors]
    competitors_out: list[dict[str, Any]] = [
        {"title": c.title, "price": float(c.price)} for c in payload.competitors
    ]

    if payload.product_id is not None:
        raw = await run_in_threadpool(fetch_product_from_api, payload.product_id)
        product_dict = normalize_dummyjson_product(raw)
        source = "dummyjson API"
    else:
        assert payload.product is not None
        product_dict = _manual_product_snapshot(payload.product)
        source = "manual"

    price = float(product_dict["price_usd"])
    stock = product_dict.get("stock")
    if isinstance(stock, float) and stock == int(stock):
        stock = int(stock)
    if not isinstance(stock, (int, type(None))):
        stock = None

    decisions = compute_simulated_decisions(price, stock, comp_tuples)
    return SimulatedDecisionResponse(
        product=product_dict,
        competitors=competitors_out,
        decisions=decisions,
        source=source,
    )
