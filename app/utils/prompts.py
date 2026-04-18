from app.models.schemas import ProductBrief

ANALYZER_SYSTEM = """You are a senior e-commerce strategy analyst for a consulting firm.
You synthesize product facts with internal playbooks and market context.
Return concise, executive-ready bullets. Avoid generic platitudes; tie claims to inputs."""

DECISION_SYSTEM = """You are a principal responsible for structured commercial decisions.
You produce explicit decisions a retailer could execute, each with rationale, confidence,
owning function, time horizon, and a measurable success metric. Prefer practical tradeoffs
over exhaustive theory."""

FORMATTER_SYSTEM = """You are a consulting engagement manager formatting findings for a client readout.
Tone: crisp, confident, and specific. The output must read like a short engagement memo."""

def analyzer_user_prompt(product_block: str, context_block: str) -> str:
    return f"""## Product
{product_block}

## Retrieved internal context (policies, benchmarks, narratives)
{context_block}

Return JSON matching this shape:
{{
  "market_signals": ["..."],
  "risks": ["..."],
  "opportunities": ["..."],
  "competitive_notes": ["..."],
  "key_metrics_to_watch": ["..."]
}}
"""


def decision_user_prompt(product_block: str, analysis_json: str) -> str:
    return f"""## Product
{product_block}

## Prior analysis (JSON)
{analysis_json}

Return JSON matching this shape (omit a key if not applicable).
For each decision block, "confidence" must be exactly one of: low, medium, high (lowercase strings).
"horizon_days" must be an integer from 1 to 365.
{{
  "pricing": {{
    "decision": "...",
    "rationale": "...",
    "confidence": "medium",
    "owner": "...",
    "horizon_days": 30,
    "success_metric": "..."
  }},
  "promotion": {{ ... }},
  "inventory_ops": {{ ... }},
  "catalog_positioning": {{ ... }},
  "customer_experience": {{ ... }}
}}
"""


def formatter_user_prompt(product_block: str, analysis_json: str, decisions_json: str) -> str:
    return f"""## Product
{product_block}

## Analysis (JSON)
{analysis_json}

## Decisions (JSON)
{decisions_json}

Return JSON at the root (no wrapper keys) with exactly this shape:
{{
  "headline": "...",
  "situation": "2-4 sentences",
  "recommendation": "2-4 sentences",
  "next_steps": ["...", "..."]
}}
"""


def format_brief_block(brief: ProductBrief) -> str:
    """Human-readable block for LLM prompts (our SKU + named competitors)."""
    p = brief.product
    lines = [
        f"title: {p.title}",
        f"description: {p.description}",
        f"category: {p.category or 'n/a'}",
        f"price_usd: {p.price_usd}",
        f"cost_usd: {p.cost_usd}",
        f"inventory_units: {p.inventory_units}",
        f"margin_target_pct: {p.margin_target_pct}",
        f"constraints: {', '.join(p.constraints) if p.constraints else 'none'}",
    ]
    if brief.competitors:
        lines.append("named_competitors:")
        for i, c in enumerate(brief.competitors, 1):
            seg = f"  {i}. {c.name}"
            if c.price_usd is not None:
                seg += f" (price_usd ~ {c.price_usd})"
            if c.positioning_notes:
                seg += f" — {c.positioning_notes}"
            if c.url:
                seg += f" [{c.url}]"
            lines.append(seg)
    return "\n".join(lines)
