"""
Preview isolation enforcement — CLAUDE_CRM_MODULE.md business rules 2 and 9.
A preview token must never reach anything outside /api/preview/*, regardless
of whether a matching route even exists. Runs after middleware/auth.py (see
main.py registration order), so request.state.is_preview is already set.

Returns 403 (not 404/401) for a preview token hitting a non-preview path —
that distinction is what proves this is enforced at the middleware layer,
not just "the route doesn't exist."
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_ALWAYS_OPEN = {"/health", "/docs", "/openapi.json", "/redoc"}


class PreviewIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _ALWAYS_OPEN:
            return await call_next(request)

        if request.state.is_preview and not request.url.path.startswith("/api/preview"):
            return JSONResponse(
                status_code=403,
                content={"detail": "Preview tokens may only access /api/preview/* routes."},
            )

        return await call_next(request)
