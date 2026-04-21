"""Smoke test for the /health endpoint.

TestClient runs the FastAPI app in-process (no real network, no port),
so this test is fast and deterministic.
"""

from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
