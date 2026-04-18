from fastapi.testclient import TestClient

from api.index import app


def test_root_serves_demo_html():
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Agentic AI Decision Engine" in r.text
    assert "/v1/decisions" in r.text
    assert "Created by Rusben Madrigal" in r.text
    assert "San José, Costa Rica" in r.text
    assert "rusbenmadrigal@gmail.com" in r.text
    assert "rusmadrigal.com" in r.text
    assert "load-overlay" in r.text
    assert "Collecting your data" in r.text
    assert "Replay tour" in r.text
    assert "starts automatically" in r.text
    assert "aide_demo_tour_v4_done" in r.text
    assert "tour-root" in r.text


def test_readiness_json():
    with TestClient(app) as client:
        r = client.get("/api/readiness")
    assert r.status_code == 200
    body = r.json()
    assert "openai_configured" in body
    assert "rag_ready" in body
    assert isinstance(body["openai_configured"], bool)
    assert isinstance(body["rag_ready"], bool)
