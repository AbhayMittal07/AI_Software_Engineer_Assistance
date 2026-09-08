"""Dashboard and system health endpoints."""
from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.cache import cache
from app.core.config import settings
from app.schemas.analysis import DashboardStats
from app.services.ai.factory import get_ai_provider
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(user: CurrentUser, session: DbSession) -> DashboardStats:
    return await DashboardService(session).stats(user)


@router.get("/health")
async def health() -> dict:
    provider = get_ai_provider()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "mysql" if not settings.is_sqlite else "sqlite",
        "cache_backend": cache.backend,
        "ai_provider": provider.name,
        "ai_enabled": provider.available,
        "ai_model": provider.text_model,
    }
