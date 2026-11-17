import ipaddress
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.api.api import api_router
from app.rate_limit import RateLimiter
from app.settings import settings
from transfermarkt_api import Transfermarkt, __version__
from transfermarkt_api.cache import CacheConfig
from transfermarkt_api.exceptions import EndpointUnavailable, NotFound, UpstreamBlocked, UpstreamError, UpstreamTimeout

access_log = logging.getLogger("uvicorn.error")
_LOG_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def _log_safe(value: str) -> str:
    """Escape control characters so caller data cannot split or forge an access-log line."""
    return _LOG_CONTROL_RE.sub(lambda match: f"\\x{ord(match.group()):02x}", value)


def client_ip(request: Request) -> str:
    """
    Address of the client calling the API, the key for rate limiting.

    `Fly-Client-IP` is used only when `TRUST_PROXY_HEADERS` is enabled, which an operator should set only where a
    trusted proxy overwrites any client-supplied copy of the header (Fly.io does). `X-Forwarded-For` is never trusted.
    The header is accepted only as a valid IP literal, so malformed values fall back to the socket peer.
    """
    peer = request.client.host if request.client else "unknown"
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("Fly-Client-IP")
        if forwarded:
            try:
                ipaddress.ip_address(forwarded)
            except ValueError:
                pass
            else:
                return forwarded
    return peer


limiter = RateLimiter(settings.RATE_LIMITING_FREQUENCY, enabled=settings.RATE_LIMITING_ENABLE)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the shared tfmkt client on startup and close it on shutdown."""
    app.state.tfmkt = Transfermarkt(
        base_url=settings.TFMKT_BASE_URL,
        timeout=settings.TFMKT_TIMEOUT_SECONDS,
        max_concurrency=settings.TFMKT_MAX_CONCURRENCY,
        cache=CacheConfig(
            ttl=settings.CACHE_TTL_SECONDS,
            reference_ttl=settings.CACHE_REFERENCE_TTL_SECONDS,
            max_entries=settings.CACHE_MAX_ENTRIES,
        ),
    )
    try:
        yield
    finally:
        await app.state.tfmkt.aclose()


app = FastAPI(
    title="Transfermarkt API",
    version=__version__,
    description="Football data from Transfermarkt's JSON API: players, clubs and competitions.",
    lifespan=lifespan,
)
# health checks and the interactive docs (the root redirect, Swagger UI and the schema it loads) are not counted
RATE_LIMIT_EXEMPT_PATHS = {
    "/",
    "/health",
    *filter(None, (app.docs_url, app.swagger_ui_oauth2_redirect_url, app.redoc_url, app.openapi_url)),
}
app.include_router(api_router)


async def sdk_error_response(request: Request, error: Exception) -> JSONResponse:
    """Translate SDK failures into the existing HTTP error contract."""
    statuses = {NotFound: 404, UpstreamBlocked: 503, UpstreamTimeout: 504, UpstreamError: 502, EndpointUnavailable: 501}
    return JSONResponse(
        {"detail": str(error)},
        status_code=next(status for error_type, status in statuses.items() if isinstance(error, error_type)),
    )


for error_type in (NotFound, UpstreamBlocked, UpstreamTimeout, UpstreamError, EndpointUnavailable):
    app.add_exception_handler(error_type, sdk_error_response)


@app.middleware("http")
async def rate_limit(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Answer 429 when the client is over its budget. All API routes share one budget; see `RATE_LIMIT_EXEMPT_PATHS`."""
    if not limiter.enabled or request.url.path in RATE_LIMIT_EXEMPT_PATHS:
        return await call_next(request)
    key = client_ip(request)
    if not limiter.hit(key):
        return JSONResponse(
            {"error": f"Rate limit exceeded: {settings.RATE_LIMITING_FREQUENCY}"},
            status_code=429,
            headers={"Retry-After": str(limiter.retry_after(key))},
        )
    return await call_next(request)


@app.middleware("http")
async def log_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Log HTTP requests using the client address resolved for rate limiting."""
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        target = _log_safe(request.url.path)
        if request.url.query:
            target = f"{target}?{_log_safe(request.url.query)}"
        access_log.info('%s - "%s %s" %d', _log_safe(client_ip(request)), _log_safe(request.method), target, status)


@app.get("/", include_in_schema=False)
def docs_redirect() -> RedirectResponse:
    """Redirect the root URL to the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", include_in_schema=False)
def health() -> dict:
    """Liveness check for the hosting platform. Does not call Transfermarkt."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
