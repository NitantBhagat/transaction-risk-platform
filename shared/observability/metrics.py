from __future__ import annotations

import time

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=("service", "method", "path", "status_code"),
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=("service", "method", "path"),
)

WORKER_RISK_ASSESSMENTS_TOTAL = Counter(
    "worker_risk_assessments_total",
    "Total risk assessments processed by the worker, by result.",
    labelnames=("result",),
)


def setup_metrics(app: FastAPI, service_name: str) -> None:
    """
    Attach basic Prometheus metrics to a FastAPI app and expose /metrics.
    """

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = request.url.path
        method = request.method
        status_code = response.status_code

        REQUEST_LATENCY.labels(service_name, method, path).observe(elapsed)
        REQUEST_COUNT.labels(service_name, method, path, str(status_code)).inc()

        return response

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

