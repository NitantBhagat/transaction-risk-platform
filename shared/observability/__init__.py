from __future__ import annotations

from fastapi import FastAPI

from shared.observability.metrics import setup_metrics
from shared.observability.tracing import instrument_fastapi_app, setup_tracing


def init_observability(app: FastAPI, service_name: str) -> None:
    """
    Initialise tracing and metrics for a FastAPI application.

    This function is intentionally lightweight and safe to call once per service.
    """
    setup_tracing(service_name=service_name)
    instrument_fastapi_app(app)
    setup_metrics(app=app, service_name=service_name)

