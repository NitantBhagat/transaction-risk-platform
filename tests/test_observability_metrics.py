from __future__ import annotations

from fastapi.testclient import TestClient

from services.ingestion_service.main import app as ingestion_app


client = TestClient(ingestion_app)


def test_metrics_endpoint_available() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    # Response should contain some standard Prometheus exposition format markers.
    body = response.text
    assert "# HELP" in body
    assert "# TYPE" in body

