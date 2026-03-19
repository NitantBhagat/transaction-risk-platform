from __future__ import annotations

from fastapi import FastAPI

from services.gateway.api.routes import router as gateway_router
from services.gateway.core.settings import get_settings
from shared.logging import init_logging
from shared.observability import init_observability


settings = get_settings()
logger = init_logging(settings.service_name)

app = FastAPI(
    title="Gateway Service",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.on_event("startup")
async def on_startup() -> None:
    init_observability(app, service_name=settings.service_name)
    logger.info("Starting gateway service", extra={"service": settings.service_name})


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Shutting down gateway service", extra={"service": settings.service_name})


app.include_router(gateway_router)

