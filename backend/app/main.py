"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import register_middleware
from app.db.session import engine, init_models

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_directories()
    await cache.connect()
    await init_models()
    try:
        from app.db.seed import seed

        await seed()
    except Exception as exc:  # noqa: BLE001 - never block startup on seeding
        logger.warning("Seeding skipped: %s", str(exc)[:250])
    logger.info(
        "%s v%s started | db=%s | cache=%s | ai=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        "sqlite" if settings.is_sqlite else "mysql",
        cache.backend,
        settings.ai_enabled,
    )
    yield
    await cache.disconnect()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-ready AI Software Engineering Assistant: repository ingestion, AI code review, "
        "documentation generation, architecture diagrams, RAG chat and PDF reporting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }
