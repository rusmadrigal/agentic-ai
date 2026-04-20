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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from app.services.seo_analysis_chain import build_seo_chain


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("Set OPENAI_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip()
    chain = build_seo_chain(
        model=model,
        api_key=os.environ["OPENAI_API_KEY"].strip(),
        temperature=0,
    )

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
