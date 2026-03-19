from __future__ import annotations

from fastapi import APIRouter, Depends

from services.risk_service.core.dependencies import settings_dependency
from services.risk_service.core.settings import RiskServiceSettings
from shared.schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Risk service health check")
async def health(
    settings: RiskServiceSettings = Depends(settings_dependency),
) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, version=settings.service_version)

