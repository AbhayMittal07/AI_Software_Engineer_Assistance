"""Security headers, request logging and rate limiting middleware."""
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import cache
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("app.request")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Resource-Policy": "cross-origin",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(duration_ms)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter backed by Redis (or memory fallback)."""

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)

        is_auth = path.startswith(f"{settings.API_V1_PREFIX}/auth/")
        limit = settings.AUTH_RATE_LIMIT_REQUESTS if is_auth else settings.RATE_LIMIT_REQUESTS
        window = (
            settings.AUTH_RATE_LIMIT_WINDOW_SECONDS if is_auth else settings.RATE_LIMIT_WINDOW_SECONDS
        )
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        bucket = int(time.time() // window)
        key = f"ratelimit:{'auth' if is_auth else 'api'}:{client_ip}:{bucket}"
        blocked, count = await cache.hit_rate_limit(key, limit, window)
        if blocked:
            logger.warning("Rate limit exceeded for %s on %s (%s)", client_ip, path, count)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {"code": "rate_limited", "message": "Too many requests, slow down.", "details": {}},
                    "detail": "Too many requests, slow down.",
                },
                headers={"Retry-After": str(window)},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(limit - count, 0))
        return response


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
