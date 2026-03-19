from __future__ import annotations

from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_configured: bool = False


def setup_tracing(service_name: str, endpoint: Optional[str] = None) -> None:
    """
    Configure OpenTelemetry tracing for the current process.

    The OTLP exporter endpoint can be configured via the optional `endpoint`
    argument or via standard OTEL_* environment variables.
    """
    global _configured
    if _configured:
        return

    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter_kwargs = {}
    if endpoint is not None:
        exporter_kwargs["endpoint"] = endpoint

    exporter = OTLPSpanExporter(**exporter_kwargs)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _configured = True


def instrument_fastapi_app(app) -> None:  # type: ignore[no-untyped-def]
    """
    Attach FastAPI-specific instrumentation to an application.
    """
    FastAPIInstrumentor.instrument_app(app)

