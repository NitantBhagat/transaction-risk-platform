from __future__ import annotations

from fastapi import APIRouter, Depends

from services.gateway.core.dependencies import settings_dependency
from services.gateway.core.settings import GatewayServiceSettings
from shared.schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Gateway service health check")
async def health(
    settings: GatewayServiceSettings = Depends(settings_dependency),
) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, version=settings.service_version)

