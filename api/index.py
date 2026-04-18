import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.models.schemas import DecisionEngineResponse, ProductBrief
from app.rag.retriever import Retriever
from app.services.orchestrator import DecisionOrchestrator

configure_logging()
logger = get_logger(__name__)

_orchestrator: Optional[DecisionOrchestrator] = None

_DEMO_HTML_PATH = _ROOT / "app" / "static" / "demo.html"

_DESCRIPTION = """
**Agentic workflow:** retrieve internal playbooks (FAISS) → analyze → structured decisions → client-ready memo.

**Stack:** FastAPI · OpenAI · FAISS · Pydantic · no external DB (MVP).

Use **POST /v1/decisions** with a `ProductBrief` JSON body, or open the **interactive demo** at `/`.
""".strip()

_TAGS_METADATA = [
    {
        "name": "demo",
        "description": "Human-friendly entry points for reviewers.",
    },
    {
        "name": "decisions",
        "description": "Structured e-commerce decision pipeline.",
    },
    {
        "name": "ops",
        "description": "Health and readiness for deploy hooks.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    configure_logging()
    if settings.openai_api_key:
        logger.info("OPENAI_API_KEY is configured")
    else:
        logger.warning(
            "OPENAI_API_KEY is not set; add it to %s or the environment for /v1/decisions.",
            _ROOT / ".env",
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
    version="0.1.0",
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


@app.get("/api/readiness", tags=["ops"])
async def readiness() -> dict:
    """Signals for UI banners and load balancers (no secrets)."""
    return {
        "openai_configured": bool(settings.openai_api_key),
        "rag_ready": _orchestrator is not None,
        "embedding_mode": settings.embedding_mode,
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
    response_model=DecisionEngineResponse,
    tags=["decisions"],
    summary="Run the full decision pipeline",
    response_description="Echoed input, retrieval hits, and a consulting-style deliverable.",
)
async def create_decision(payload: ProductBrief) -> DecisionEngineResponse:
    """
    Accepts a **ProductBrief** at the JSON root (`product` + `competitors`).

    Returns structured analysis, explicit decision objects, and an executive summary suitable for a client readout.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured; agents cannot run in this environment.",
        )
    if _orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="RAG index is not available. Run `python scripts/build_index.py` and redeploy.",
        )
    try:
        return await _orchestrator.run(payload)
    except RuntimeError as exc:
        logger.exception("decision pipeline failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
