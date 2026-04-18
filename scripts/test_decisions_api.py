#!/usr/bin/env python3
"""
Smoke test for POST /v1/decisions against a running local server.

Usage (from repo root, with API up on port 8000):

    python scripts/test_decisions_api.py
    python scripts/test_decisions_api.py http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import sys
from typing import Any

import requests

DEFAULT_BASE = "http://127.0.0.1:8000"
REQUEST_TIMEOUT_SEC = 120

# Root JSON body = ProductBrief: { "product": {...}, "competitors": [...] }
SAMPLE_PAYLOAD: dict[str, Any] = {
    "product": {
        "sku": "TEST-001",
        "title": "Merino crewneck sweater — limited colors",
        "description": "Mid-weight merino blend; strong email repeats; sizing content is thin.",
        "category": "Apparel / Knitwear",
        "price_usd": 89.0,
        "cost_usd": 38.0,
        "inventory_units": 4200,
        "margin_target_pct": 52.0,
        "constraints": ["Avoid sitewide 20% coupons", "Premium adjacency"],
    },
    "competitors": [
        {
            "name": "Nordic Knit Co. Crew",
            "price_usd": 78.0,
            "positioning_notes": "Frequent promos; stronger PDP sizing content.",
        }
    ],
}


def _print_json(label: str, data: Any) -> None:
    print(label)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE).rstrip("/")
    url = f"{base}/v1/decisions"

    print(f"POST {url}\n")

    try:
        response = requests.post(
            url,
            json=SAMPLE_PAYLOAD,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(f"Status code: {response.status_code}\n")

    try:
        body = response.json()
    except json.JSONDecodeError:
        print("Response body (not JSON):")
        print(response.text[:8000])
        return 1 if not response.ok else 0

    _print_json("JSON response:", body)

    if not response.ok:
        return 1

    required_keys = ("product", "retrieval", "deliverable", "workflow_version")
    missing = [k for k in required_keys if k not in body]
    if missing:
        print(f"\nWarning: expected top-level keys missing: {missing}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
