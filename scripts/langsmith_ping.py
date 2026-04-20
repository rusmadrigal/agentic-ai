#!/usr/bin/env python3
"""
LangChain SEO analysis chain (ChatOpenAI + ChatPromptTemplate).

From the repo root:

  pip install -r requirements.txt
  python scripts/langsmith_ping.py

LangSmith: set LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY, and LANGCHAIN_PROJECT in .env.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from langchain_core.prompts import ChatPromptTemplate
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


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("Set OPENAI_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip()
    llm = ChatOpenAI(model=model, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ],
    )
    chain = prompt | llm

    # Realistic snapshot (no live crawl): common misalignment between intent and on-page copy.
    page = {
        "url": "https://www.hometowncoffee.com/menu/pastries",
        "keyword": "best espresso beans for home brewing",
        "title": "Pastries & Bakery Menu | Hometown Coffee Roasters",
        "h1": "Fresh Pastries Baked Daily",
    }

    result = chain.invoke(page)
    print(result.content)


if __name__ == "__main__":
    main()
