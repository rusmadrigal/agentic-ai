from app.agents._openai_json import complete_json_model
from app.models.schemas import AnalyzerOutput, ProductBrief, RetrievedChunk
from app.utils.prompts import ANALYZER_SYSTEM, analyzer_user_prompt, format_brief_block


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for c in chunks:
        blocks.append(f"### {c.title} (id={c.id}, score={c.score:.3f})\n{c.text}")
    return "\n\n".join(blocks) if blocks else "(no retrieved context)"


async def run_analyzer(product: ProductBrief, chunks: list[RetrievedChunk]) -> AnalyzerOutput:
    product_block = format_brief_block(product)
    context_block = _format_context(chunks)
    user = analyzer_user_prompt(product_block, context_block)
    return await complete_json_model(
        system=ANALYZER_SYSTEM,
        user=user,
        model_type=AnalyzerOutput,
        temperature=0.25,
    )
