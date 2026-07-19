"""
JWT decode + request.state population.
Runs before middleware/preview.py (see main.py registration order — Starlette
executes the LAST-added middleware FIRST). Does not reject requests on its
own for missing auth entirely; it only decodes whatever token is present and
sets state — except for the two checks that are inherently middleware-layer
concerns (missing/invalid Bearer token, and the acting-client-id checks
below), which return here rather than being re-implemented per route.
"""
from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import TokenError, decode_token
from app.db.models.platform import PlatformAccount
from app.db.session import get_engine

OPEN_PATHS = {
    "/health", "/docs", "/openapi.json", "/redoc",
    "/api/preview/register", "/auth/login", "/oauth/callback",
}

# Prefix-matched open paths — for routes with a path parameter (the {client_id}
# in Smartlead's webhook URL), so a fixed OPEN_PATHS set membership check can't
# apply. Auth here is the X-Webhook-Secret header the route itself checks, not
# a Bearer token — Smartlead has no way to hold a per-client JWT.
OPEN_PATH_PREFIXES = ("/api/email-events/sync/",)

# Roles with no single client_id in their token — they act on a client
# specified per-request via X-Acting-Client-Id instead.
_ACTING_CLIENT_ROLES = {"support_manager", "cc_admin"}


async def _lookup_client_db_url(client_id: str) -> str | None:
    """Looks up PlatformAccount.client_db_url from the platform DB on every
    request rather than trusting a URL baked into the JWT — accounts can be
    deactivated or reprovisioned after a token was issued."""
    try:
        client_uuid = uuid.UUID(client_id)
    except (ValueError, TypeError):
        return None

    _, sessionmaker = get_engine(settings.platform_database_url)
    async with sessionmaker() as session:
        account = (
            await session.execute(select(PlatformAccount).where(PlatformAccount.id == client_uuid))
        ).scalar_one_or_none()
        return account.client_db_url if account else None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.role = None
        request.state.is_preview = False
        request.state.client_db_url = None
        request.state.client_id = None
        request.state.claims = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            try:
                claims = decode_token(token)
            except TokenError as exc:
                return JSONResponse(status_code=401, content={"detail": str(exc)})

            request.state.claims = claims
            role = claims.get("role")
            request.state.role = role
            request.state.is_preview = bool(claims.get("is_preview"))

            if request.state.is_preview:
                # client_db claim holds a preview DB *name*
                # (e.g. "ias_crm_preview_meridian") — resolve to a URL.
                request.state.client_db_url = settings.preview_db_urls.get(claims.get("client_db"))
                request.state.client_id = "preview"

            elif role in _ACTING_CLIENT_ROLES:
                # X-Acting-Client-Id is only required by routes that actually
                # need tenant-DB routing (dashboard/targets/pipeline, via
                # get_tenant_db) — NOT platform-only routes like POST
                # /api/accounts (creating a client — there's no client to act
                # as yet). So the header is optional here; get_tenant_db()
                # itself raises a clean 400 if a tenant-DB route is hit
                # without client_db_url having been resolved.
                acting_client_id = request.headers.get("X-Acting-Client-Id")
                if acting_client_id:
                    if role == "support_manager" and acting_client_id not in (claims.get("assigned_clients") or []):
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "Not assigned to this client."},
                        )
                    # cc_admin's permission is "*" — no assigned_clients
                    # membership check applies to it, any existing client_id
                    # is reachable.
                    db_url = await _lookup_client_db_url(acting_client_id)
                    if db_url is None:
                        return JSONResponse(status_code=403, content={"detail": "Client account not found."})
                    request.state.client_db_url = db_url
                    request.state.client_id = acting_client_id

            else:
                # client_admin | client_team | client_readonly — single-client token
                client_id = claims.get("client_id")
                db_url = await _lookup_client_db_url(client_id) if client_id else None
                if db_url is None:
                    return JSONResponse(status_code=403, content={"detail": "Client account not found."})
                request.state.client_db_url = db_url
                request.state.client_id = client_id

        elif request.url.path not in OPEN_PATHS and not request.url.path.startswith(OPEN_PATH_PREFIXES):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization: Bearer <token> header."},
            )

        return await call_next(request)
