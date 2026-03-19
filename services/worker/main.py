from __future__ import annotations

import asyncio

from fastapi import FastAPI

from services.worker.api.routes import router as worker_router
from services.worker.core.settings import get_settings
from services.worker.risk_pipeline import run_risk_pipeline
from shared.logging import init_logging
from shared.observability import init_observability


settings = get_settings()
logger = init_logging(settings.service_name)

app = FastAPI(
    title="Worker Service",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.on_event("startup")
async def on_startup() -> None:
    init_observability(app, service_name=settings.service_name)
    logger.info("Starting worker service", extra={"service": settings.service_name})


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Shutting down worker service", extra={"service": settings.service_name})


app.include_router(worker_router)


async def _run_worker() -> None:
    logger.info("Starting risk pipeline loop")
    try:
        await run_risk_pipeline()
    except Exception:
        logger.exception("Risk pipeline loop crashed")
        raise
    finally:
        logger.info("Risk pipeline loop stopped")


def main() -> None:
    try:
        asyncio.run(_run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted; exiting")


if __name__ == "__main__":
    main()

