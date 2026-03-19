from __future__ import annotations

from fastapi.testclient import TestClient

from services.ingestion_service.main import app


client = TestClient(app)


def test_ingestion_service_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ingestion-service"
    assert "version" in body

