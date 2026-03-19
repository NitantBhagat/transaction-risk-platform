from __future__ import annotations

from fastapi.testclient import TestClient

from services.analytics_service.main import app


client = TestClient(app)


def test_analytics_service_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "analytics-service"
    assert "version" in body

