"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    APP_NAME: str = "AI Software Engineering Assistant"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # Database: MySQL in production/docker, SQLite for zero-config local runs.
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BACKEND_DIR / 'data' / 'app.db'}"
    DB_ECHO: bool = False

    # Security
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # Bootstrap admin
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "Admin@12345"
    DEMO_EMAIL: str = "demo@example.com"
    DEMO_PASSWORD: str = "Demo@12345"

    # CORS
    CORS_ORIGINS: str = "*"

    # Redis cache (optional - falls back to in-process cache)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 200
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUTH_RATE_LIMIT_REQUESTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # AI provider
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_TEXT_MODEL: str = "gemini-3.6-flash"
    GEMINI_REASONING_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"
    AI_MAX_OUTPUT_TOKENS: int = 8192
    AI_REQUEST_TIMEOUT: int = 240

    # Vector store
    CHROMA_PATH: str = str(BACKEND_DIR / "data" / "chroma")
    RAG_TOP_K: int = 6
    RAG_CHUNK_SIZE: int = 1600
    RAG_CHUNK_OVERLAP: int = 200
    RAG_MAX_CHUNKS_PER_REPO: int = 400

    # Storage
    STORAGE_DIR: str = str(BACKEND_DIR / "storage")
    MAX_UPLOAD_MB: int = 100
    MAX_FILES_PER_REPO: int = 4000
    MAX_FILE_BYTES_FOR_AI: int = 60_000
    MAX_ANALYZED_FILES_FOR_AI: int = 18

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalise_db_url(cls, value: str) -> str:
        if value.startswith("mysql://"):
            return value.replace("mysql://", "mysql+aiomysql://", 1)
        if value.startswith("mysql+pymysql://"):
            return value.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
        if value.startswith("sqlite:///"):
            return value.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _normalise_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"debug", "development", "dev"}:
                return True
            if normalized in {"release", "production", "prod"}:
                return False
        return value

    @property
    def cors_origin_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "*").strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY.strip())

    @property
    def upload_dir(self) -> Path:
        return Path(self.STORAGE_DIR) / "uploads"

    @property
    def repo_dir(self) -> Path:
        return Path(self.STORAGE_DIR) / "repositories"

    @property
    def report_dir(self) -> Path:
        return Path(self.STORAGE_DIR) / "reports"

    @property
    def diagram_dir(self) -> Path:
        return Path(self.STORAGE_DIR) / "diagrams"

    def ensure_directories(self) -> None:
        for path in (
            self.upload_dir,
            self.repo_dir,
            self.report_dir,
            self.diagram_dir,
            Path(self.CHROMA_PATH),
            BACKEND_DIR / "data",
        ):
            Path(path).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()
