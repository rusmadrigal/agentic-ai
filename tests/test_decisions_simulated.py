from unittest.mock import patch

from fastapi.testclient import TestClient

from api.index import app

_DUMMY_JSON = {
    "id": 99,
    "title": "Test Product",
    "description": "Desc",
    "price": 120.5,
    "stock": 40,
    "brand": "Acme",
    "category": "electronics",
    "thumbnail": "https://example.com/t.jpg",
    "rating": 4.5,
}


def test_post_decisions_with_product_id_uses_dummyjson():
    with TestClient(app) as client:
        with patch("app.integrations.dummyjson.requests.get") as mock_get:
            mock_resp = mock_get.return_value
            mock_resp.status_code = 200
            mock_resp.json.return_value = _DUMMY_JSON
            mock_resp.raise_for_status = lambda: None

            r = client.post(
                "/v1/decisions",
                json={
                    "product_id": 99,
                    "competitors": [{"title": "Brand A", "price": 100}, {"title": "Brand B", "price": 130}],
                },
            )

    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "dummyjson API"
    assert body["product"]["title"] == "Test Product"
    assert body["product"]["price_usd"] == 120.5
    assert len(body["competitors"]) == 2
    assert "decisions" in body
    assert body["decisions"]["pricing_strategy"]
    assert "recommended_price" in body["decisions"]
    mock_get.assert_called_once()


def test_post_decisions_manual_product():
    with TestClient(app) as client:
        r = client.post(
            "/v1/decisions",
            json={
                "product": {
                    "title": "Manual SKU",
                    "description": "Nice",
                    "category": "Home",
                    "price_usd": 50,
                    "inventory_units": 100,
                    "constraints": [],
                },
                "competitors": [{"title": "Other", "price": 55}],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "manual"
    assert body["product"]["title"] == "Manual SKU"
    assert body["decisions"]["reasoning"]


def test_external_product_endpoint():
    with TestClient(app) as client:
        with patch("app.integrations.dummyjson.requests.get") as mock_get:
            mock_resp = mock_get.return_value
            mock_resp.status_code = 200
            mock_resp.json.return_value = _DUMMY_JSON
            mock_resp.raise_for_status = lambda: None

            r = client.get("/api/external-products/99")
    assert r.status_code == 200
    assert r.json()["title"] == "Test Product"
