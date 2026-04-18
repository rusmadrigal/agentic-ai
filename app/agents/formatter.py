import json

from app.agents._openai_json import complete_json_model
from app.models.schemas import AnalyzerOutput, DecisionMakerOutput, FormatterEnvelope, ExecutiveSummary, ProductBrief
from app.utils.prompts import FORMATTER_SYSTEM, formatter_user_prompt, format_brief_block


async def run_formatter(
    product: ProductBrief,
    analysis: AnalyzerOutput,
    decisions: DecisionMakerOutput,
) -> ExecutiveSummary:
    product_block = format_brief_block(product)
    analysis_json = json.dumps(analysis.model_dump(), ensure_ascii=False)
    decisions_json = json.dumps(decisions.model_dump(), ensure_ascii=False)
    user = formatter_user_prompt(product_block, analysis_json, decisions_json)
    envelope = await complete_json_model(
        system=FORMATTER_SYSTEM,
        user=user,
        model_type=FormatterEnvelope,
        temperature=0.35,
    )
    try:
        return envelope.to_executive_summary()
    except ValueError as exc:
        raise RuntimeError("Formatter model returned an unusable executive summary shape") from exc
