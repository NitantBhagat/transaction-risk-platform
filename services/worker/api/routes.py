from __future__ import annotations

from fastapi import APIRouter, Depends

from services.worker.core.dependencies import settings_dependency
from services.worker.core.settings import WorkerServiceSettings
from shared.schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Worker service health check")
async def health(
    settings: WorkerServiceSettings = Depends(settings_dependency),
) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, version=settings.service_version)

