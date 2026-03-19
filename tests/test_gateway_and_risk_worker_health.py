from __future__ import annotations

from fastapi.testclient import TestClient

from services.analytics_service.main import app as analytics_app
from services.gateway.main import app as gateway_app
from services.risk_service.main import app as risk_app
from services.worker.main import app as worker_app


def test_gateway_health() -> None:
    client = TestClient(gateway_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "gateway"


def test_risk_service_health() -> None:
    client = TestClient(risk_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "risk-service"


def test_worker_health() -> None:
    client = TestClient(worker_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "worker"

