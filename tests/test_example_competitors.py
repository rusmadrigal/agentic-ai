from unittest.mock import patch

from fastapi.testclient import TestClient

from api.index import app
from app.integrations.dummyjson import fetch_example_competitors


def test_get_example_competitors_endpoint():
    sample = [
        {"title": "X · Alpha", "price": 40.0},
        {"title": "Y · Beta", "price": 60.0},
    ]
    with TestClient(app) as client:
        with patch("api.index.fetch_example_competitors", return_value=sample):
            r = client.get("/api/example-competitors/99?limit=2")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "dummyjson"
    assert body["product_id"] == 99
    assert body["competitors"] == sample


def test_fetch_example_competitors_filters_self_and_respects_limit():
    calls = []

    def fake_get(url, params=None, timeout=None):
        class R:
            def __init__(self, payload, code=200):
                self.status_code = code
                self._payload = payload

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError("http error")

            def json(self):
                return self._payload

        u = str(url)
        calls.append(u)
        if u.endswith("/products/99") and "/category/" not in u:
            return R({"id": 99, "title": "Mine", "price": 50, "category": "beauty", "brand": "B"})
        if "/products/category/" in u:
            return R(
                {
                    "products": [
                        {"id": 1, "title": "Other", "price": 40, "brand": "X"},
                        {"id": 99, "title": "Mine", "price": 50, "brand": "B"},
                        {"id": 2, "title": "Other2", "price": 60, "brand": "Y"},
                        {"id": 3, "title": "Other3", "price": 70, "brand": "Z"},
                    ]
                }
            )
        return R({}, 404)

    with patch("app.integrations.dummyjson.requests.get", side_effect=fake_get):
        rows = fetch_example_competitors(99, limit=2)

    assert len(rows) == 2
    assert [r["price"] for r in rows] == [40.0, 60.0]
    assert rows[0]["title"].startswith("X ·")
