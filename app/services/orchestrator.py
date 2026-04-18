from app.agents.analyzer import run_analyzer
from app.agents.decision_maker import run_decision_maker
from app.agents.formatter import run_formatter
from app.core.config import settings
from app.models.schemas import ClientDeliverable, DecisionEngineResponse, ProductBrief
from app.rag.retriever import Retriever


class DecisionOrchestrator:
    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    async def run(self, product: ProductBrief) -> DecisionEngineResponse:
        chunks = await self._retriever.retrieve(product, k=4)
        analysis = await run_analyzer(product, chunks)
        decisions = await run_decision_maker(product, analysis)
        executive_summary = await run_formatter(product, analysis, decisions)

        deliverable = ClientDeliverable(
            executive_summary=executive_summary,
            analysis=analysis,
            decisions=decisions,
            appendix={
                "models": {
                    "chat": settings.openai_chat_model,
                    "embedding": settings.openai_embedding_model,
                    "embedding_mode": settings.embedding_mode,
                },
                "retrieval": [c.model_dump() for c in chunks],
            },
        )

        return DecisionEngineResponse(
            product=product,
            retrieval=chunks,
            deliverable=deliverable,
        )
