"""Fetch catalog products from DummyJSON (external demo data)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests
from fastapi import HTTPException

DUMMYJSON_PRODUCT_URL = "https://dummyjson.com/products/{product_id}"
DUMMYJSON_CATEGORY_URL = "https://dummyjson.com/products/category/{category}"
DUMMYJSON_PRODUCTS_URL = "https://dummyjson.com/products"


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


def _category_slug_from_product(raw: dict[str, Any]) -> str:
    cat = raw.get("category")
    if isinstance(cat, dict):
        cat = cat.get("name") or cat.get("slug")
    return str(cat or "").strip()


def _competitor_row(p: dict[str, Any]) -> dict[str, Any]:
    brand = (p.get("brand") or "").strip()
    title = (p.get("title") or "Product").strip()
    label = f"{brand} · {title}" if brand else title
    price = float(p.get("price") or 0)
    return {"title": label[:200], "price": round(price, 2)}


def fetch_example_competitors(product_id: int, limit: int = 3) -> list[dict[str, Any]]:
    """
    Return other DummyJSON products as example peers (same category when possible).

    Used for MVP demos so users do not have to type competitor rows by hand.
    """
    if limit < 1:
        limit = 1
    if limit > 8:
        limit = 8

    raw = fetch_product_from_api(product_id)
    category = _category_slug_from_product(raw)
    seen: set[int] = {int(product_id)}
    out: list[dict[str, Any]] = []

    def _append_from_products(products: list[dict[str, Any]]) -> None:
        for p in products:
            if len(out) >= limit:
                return
            pid = p.get("id")
            if pid is None:
                continue
            try:
                pid_i = int(pid)
            except (TypeError, ValueError):
                continue
            if pid_i in seen:
                continue
            seen.add(pid_i)
            out.append(_competitor_row(p))

    if category:
        url = DUMMYJSON_CATEGORY_URL.format(category=quote(category, safe=""))
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                _append_from_products(list(data.get("products") or []))
        except requests.RequestException:
            pass

    if len(out) < limit:
        try:
            skip = max(0, (product_id * 3) % 90)
            response = requests.get(
                DUMMYJSON_PRODUCTS_URL,
                params={"limit": 40, "skip": skip},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            _append_from_products(list(data.get("products") or []))
        except (requests.RequestException, ValueError, TypeError):
            pass

    if not out:
        raise HTTPException(
            status_code=502,
            detail="Could not load example competitors from DummyJSON.",
        )
    return out
