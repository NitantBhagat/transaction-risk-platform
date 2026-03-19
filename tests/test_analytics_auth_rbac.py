from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from services.analytics_service.main import app
from shared.config import get_base_settings


client = TestClient(app)


def _make_token(roles: list[str], expired: bool = False) -> str:
    settings = get_base_settings()
    now = datetime.now(tz=timezone.utc)
    if expired:
        iat = now - timedelta(minutes=10)
        exp = now - timedelta(minutes=5)
    else:
        iat = now
        exp = now + timedelta(minutes=5)
    payload = {
        "sub": "user-123",
        "roles": roles,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)


def test_analytics_no_token_401() -> None:
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_analytics_malformed_token_401() -> None:
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_analytics_expired_token_401() -> None:
    token = _make_token(["analyst"], expired=True)
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_analytics_unauthorized_role_403() -> None:
    token = _make_token(["readonly"])
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_analytics_admin_success() -> None:
    token = _make_token(["admin"])
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code != 401
    assert response.status_code != 403


def test_analytics_analyst_success() -> None:
    token = _make_token(["analyst"])
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code != 401
    assert response.status_code != 403


def test_analytics_health_public() -> None:
    response = client.get("/health")
    assert response.status_code == 200

