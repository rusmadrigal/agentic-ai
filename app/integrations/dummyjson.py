"""Fetch catalog products from DummyJSON (external demo data)."""

from __future__ import annotations

from typing import Any

import requests
from fastapi import HTTPException

DUMMYJSON_PRODUCT_URL = "https://dummyjson.com/products/{product_id}"


def fetch_product_from_api(product_id: int) -> dict[str, Any]:
    url = DUMMYJSON_PRODUCT_URL.format(product_id=product_id)
    try:
        response = requests.get(url, timeout=20)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"DummyJSON request failed: {exc}") from exc
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Product not found on DummyJSON.")
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"DummyJSON returned {response.status_code}",
        ) from exc
    return response.json()


def normalize_dummyjson_product(data: dict[str, Any]) -> dict[str, Any]:
    price = float(data.get("price") or 0)
    stock = data.get("stock")
    if stock is not None:
        try:
            stock = int(stock)
        except (TypeError, ValueError):
            stock = None
    cat = data.get("category")
    if isinstance(cat, dict):
        cat = cat.get("name") or str(cat)
    if cat is None:
        cat = ""
    return {
        "id": data.get("id"),
        "title": data.get("title") or "Unknown product",
        "description": (data.get("description") or "")[:8000],
        "category": str(cat),
        "brand": data.get("brand") or "",
        "price_usd": price,
        "stock": stock,
        "sku": str(data.get("id")) if data.get("id") is not None else None,
        "thumbnail": data.get("thumbnail"),
        "rating": data.get("rating"),
    }
