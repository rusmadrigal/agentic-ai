import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.integrations.dummyjson import (
    fetch_example_competitors,
    fetch_product_from_api,
    normalize_dummyjson_product,
)
from app.models.schemas import Product
from app.models.simulated import SimulatedDecisionsBlock, SimulatedDecisionRequest, SimulatedDecisionResponse
from app.rag.retriever import Retriever
from app.services.orchestrator import DecisionOrchestrator
from app.services.ai_decision_engine import generate_ai_decision, parse_ai_response
from app.services.rule_decisions import compute_simulated_decisions

configure_logging()
logger = get_logger(__name__)

_orchestrator: Optional[DecisionOrchestrator] = None

_DEMO_HTML_PATH = _ROOT / "app" / "static" / "demo.html"

_DESCRIPTION = """
**Decision flow:** ingest product context (DummyJSON or manual) → **LLM pricing strategist** (when `OPENAI_API_KEY` is set and `use_llm` is true or omitted) or **rule-based** simulated logic.

Structured JSON always includes pricing strategy, recommended price, promotion, inventory action, and reasoning. Optional **RAG + agents** remain for extension.

Open **`/`** for the interactive workflow, or **POST /v1/decisions** with `product_id` or `product`, competitor prices, and optional `use_llm`.
""".strip()

_TAGS_METADATA = [
    {
        "name": "demo",
        "description": "Human-friendly entry points for reviewers.",
    },
    {
        "name": "decisions",
        "description": "Commercial decisions (LLM or rule-based): pricing, promo, inventory.",
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


def _resolve_use_llm_flag(requested: Optional[bool]) -> bool:
    """True = OpenAI path; False = rules. None = auto from settings."""
    if requested is False:
        return False
    if requested is True:
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    "OpenAI is not configured (missing OPENAI_API_KEY). "
                    "Set the key or pass use_llm=false for rule-based decisions."
                ),
            )
        return True
    return bool(settings.openai_api_key)


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
        logger.info(
            "OPENAI_API_KEY is configured; POST /v1/decisions uses the LLM by default when use_llm is omitted.",
        )
    else:
        logger.warning(
            "OPENAI_API_KEY is not set; /v1/decisions uses simulated logic unless use_llm=false is sent explicitly.",
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


@app.get("/api/example-competitors/{product_id}", tags=["external"])
async def get_example_competitors(product_id: int, limit: int = 3) -> dict[str, Any]:
    """
    Suggest peer rows (title + USD price) from other DummyJSON products, same category when possible.

    For demo / meeting use; replaces hand-typed competitor examples.
    """
    if limit < 1:
        limit = 1
    if limit > 8:
        limit = 8
    rows = await run_in_threadpool(fetch_example_competitors, product_id, limit)
    return {
        "product_id": product_id,
        "competitors": rows,
        "source": "dummyjson",
    }


@app.get("/api/readiness", tags=["ops"])
async def readiness() -> dict:
    """Signals for UI banners and load balancers (no secrets)."""
    return {
        "openai_configured": bool(settings.openai_api_key),
        "llm_decisions_ready": bool(settings.openai_api_key),
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


def _langsmith_ping_sync() -> str:
    """Single ChatOpenAI invoke for LangSmith smoke tests (sync; run in threadpool)."""
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    out = llm.invoke(
        [HumanMessage(content="Say hello and confirm the system is working")],
    )
    return str(out.content)


@app.get("/debug/langsmith-ping", tags=["ops"])
async def langsmith_ping() -> dict[str, str]:
    """
    Minimal LangChain LLM call. Enable LangSmith with LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is required for this route.",
        )
    reply = await run_in_threadpool(_langsmith_ping_sync)
    return {"reply": reply}


@app.post(
    "/v1/decisions",
    response_model=SimulatedDecisionResponse,
    tags=["decisions"],
    summary="Generate commercial decisions (LLM or simulated)",
    response_description="Product context, competitor list, and structured pricing / promo / inventory decisions.",
)
async def create_decision(payload: SimulatedDecisionRequest) -> SimulatedDecisionResponse:
    """
    Provide **`product_id`** to pull live data from DummyJSON, or a manual **`product`** object.
    Competitors use **`title`** + **`price`** (USD).

    **`use_llm`:** `true` requires `OPENAI_API_KEY`. `false` forces rule-based logic. Omitted uses the LLM when a key is configured.
    """
    use_llm = _resolve_use_llm_flag(payload.use_llm)
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

    if use_llm:
        try:
            raw_text = await run_in_threadpool(generate_ai_decision, product_dict, competitors_out)
            parsed = parse_ai_response(raw_text, fallback_price=price)
            decisions = SimulatedDecisionsBlock.model_validate(parsed)
        except Exception as exc:
            logger.exception("LLM decision failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail=f"LLM decision failed: {exc!s}. Try again or use use_llm=false.",
            ) from exc
        engine: Literal["llm", "simulated"] = "llm"
    else:
        decisions = compute_simulated_decisions(price, stock, comp_tuples)
        engine = "simulated"

    return SimulatedDecisionResponse(
        product=product_dict,
        competitors=competitors_out,
        decisions=decisions,
        source=source,
        decision_engine=engine,
    )
