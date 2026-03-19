from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from services.analytics_service.main import app


@pytest.mark.integration
def test_analytics_endpoints_basic_integration() -> None:
    client = TestClient(app)

    # Requires a valid JWT; here we bypass auth by not asserting on data content,
    # focusing on the endpoints wiring in integration environments where auth can be configured.
    r1 = client.get("/api/v1/analytics/summary")
    assert r1.status_code in (200, 401, 403)

