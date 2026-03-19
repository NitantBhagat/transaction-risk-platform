from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from shared.auth import get_current_user, require_roles
from shared.config import get_base_settings
from shared.schemas.auth import RoleEnum, UserContext


app = FastAPI()


@app.get("/me")
async def read_me(user: UserContext = Depends(get_current_user)) -> dict[str, str]:
    return {"user_id": user.user_id}


@app.get("/admin-only", dependencies=[Depends(require_roles([RoleEnum.ADMIN]))])
async def admin_only() -> dict[str, str]:
    return {"status": "ok"}


client = TestClient(app)


def _make_token(roles: list[str]) -> str:
    settings = get_base_settings()
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": "user-123",
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)


def test_current_user_parses_token() -> None:
    token = _make_token(["analyst"])
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user_id": "user-123"}


def test_require_roles_allows_admin() -> None:
    token = _make_token(["admin"])
    response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_require_roles_blocks_non_admin() -> None:
    token = _make_token(["analyst"])
    response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_missing_token_returns_401() -> None:
    response = client.get("/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_malformed_token_returns_401() -> None:
    # Not a valid JWT
    response = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_expired_token_returns_401() -> None:
    settings = get_base_settings()
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": "user-123",
        "roles": ["analyst"],
        "iat": int((now - timedelta(minutes=10)).timestamp()),
        "exp": int((now - timedelta(minutes=5)).timestamp()),
    }
    expired_token = jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)
    response = client.get("/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"

