import json

from app.agents._openai_json import complete_json_model
from app.models.schemas import AnalyzerOutput, DecisionMakerOutput, ProductBrief
from app.utils.prompts import DECISION_SYSTEM, decision_user_prompt, format_brief_block


async def run_decision_maker(product: ProductBrief, analysis: AnalyzerOutput) -> DecisionMakerOutput:
    product_block = format_brief_block(product)
    analysis_json = json.dumps(analysis.model_dump(), ensure_ascii=False)
    user = decision_user_prompt(product_block, analysis_json)
    return await complete_json_model(
        system=DECISION_SYSTEM,
        user=user,
        model_type=DecisionMakerOutput,
        temperature=0.2,
    )
