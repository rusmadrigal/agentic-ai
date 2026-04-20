"""
Shared LangChain SEO analysis chain (prompt | ChatOpenAI).

Used by `scripts/langsmith_ping.py` and `GET /debug/langsmith-ping`.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """You are a Senior Technical SEO Consultant with 10+ years of experience.

You analyze webpages and provide structured, prioritized, and actionable SEO insights.

You evaluate:

* Keyword targeting
* Title optimization
* Heading structure
* Content relevance
* Internal linking opportunities

You MUST:

* Prioritize issues (High / Medium / Low)
* Explain impact (rankings, traffic, conversions)
* Provide actionable recommendations (specific changes)"""

USER_PROMPT = """Analyze this page:

URL: {url}
Keyword: {keyword}
Title: {title}
H1: {h1}

Output:

1. Summary (2-3 lines)
2. Issues (High / Medium / Low)
3. Recommendations
4. Quick Wins"""


def build_seo_chain(*, model: str, api_key: str, temperature: float = 0.0) -> Runnable:
    """Single chain: ChatPromptTemplate | ChatOpenAI (LangSmith picks up env automatically)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ],
    )
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=temperature)
    return prompt | llm
