"""
Mautic API client — pushes CRM preview-signup leads into Mautic as contacts
and adds them to a segment, so paid campaigns can be built off the list.

Mautic's OAuth2 implementation only supports the "Authorization Code" grant
(no client_credentials grant), so a human has to authorize once via browser
(see scripts/mautic_authorize.py, and api/routes/oauth.py which completes
the exchange server-side because Mautic expires codes too fast for a
manual copy-paste) to mint the initial refresh token. After that, this
module transparently refreshes the access token as needed.

The refresh token is stored in the platform DB (platform_integration_tokens),
not a .env file — the production container's filesystem is rebuilt on every
deploy, so a file write there would silently lose the token on the next
`git push`. Mautic rotates the refresh token on every use and invalidates
the old one, so the new one is persisted each time or the next refresh
would fail with an already-used-token error.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.db.models.platform import PlatformIntegrationToken
from app.db.session import get_engine

logger = logging.getLogger(__name__)

_TOKEN_PATH = "/oauth/v2/token"
_PROVIDER = "mautic"


class MauticNotConfigured(RuntimeError):
    pass


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code >= 400:
        raise RuntimeError(f"Mautic request failed ({resp.status_code}) for {resp.url}: {resp.text}")


def authorize_url() -> str:
    return (
        f"{settings.mautic_base_url}/oauth/v2/authorize"
        f"?client_id={settings.mautic_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.mautic_redirect_uri}"
    )


async def exchange_code_for_tokens(code: str) -> dict:
    """One-time authorization-code exchange — see scripts/mautic_authorize.py."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.mautic_base_url}{_TOKEN_PATH}",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.mautic_client_id,
                "client_secret": settings.mautic_client_secret,
                "redirect_uri": settings.mautic_redirect_uri,
                "code": code,
            },
        )
    _raise_for_status(resp)
    tokens = resp.json()
    _persist_refresh_token(tokens["refresh_token"])
    return tokens


async def _refresh_access_token() -> str:
    refresh_token = await _load_refresh_token()
    if not refresh_token:
        raise MauticNotConfigured(
            "No Mautic refresh token on file — run scripts/mautic_authorize.py once to authorize."
        )
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.mautic_base_url}{_TOKEN_PATH}",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.mautic_client_id,
                "client_secret": settings.mautic_client_secret,
                "refresh_token": refresh_token,
            },
        )
    _raise_for_status(resp)
    tokens = resp.json()
    await _persist_refresh_token(tokens["refresh_token"])
    return tokens["access_token"]


async def _load_refresh_token() -> str | None:
    _, sessionmaker = get_engine(settings.platform_database_url)
    async with sessionmaker() as session:
        row = (
            await session.execute(
                select(PlatformIntegrationToken).where(PlatformIntegrationToken.provider == _PROVIDER)
            )
        ).scalar_one_or_none()
        return row.refresh_token if row else None


async def _persist_refresh_token(new_token: str) -> None:
    _, sessionmaker = get_engine(settings.platform_database_url)
    async with sessionmaker() as session:
        stmt = pg_insert(PlatformIntegrationToken).values(provider=_PROVIDER, refresh_token=new_token)
        stmt = stmt.on_conflict_do_update(
            index_elements=[PlatformIntegrationToken.provider],
            set_={"refresh_token": new_token, "updated_at": func.now()},
        )
        await session.execute(stmt)
        await session.commit()


async def push_lead(*, name: str, email: str, deal_type: str, raise_target: int) -> None:
    """Create-or-update a Mautic contact for a preview signup and add them to
    the configured segment. Best-effort: logs and swallows failures so a
    Mautic outage never blocks registration — this runs after the
    registration record is already committed."""
    if not settings.mautic_base_url or not settings.mautic_client_id:
        logger.warning("mautic-push skipped: MAUTIC_* not configured")
        return

    try:
        token = await _refresh_access_token()
    except Exception:
        logger.exception("mautic-push failed: could not obtain access token")
        return

    first, _, last = name.strip().partition(" ")
    payload = {
        "firstname": first,
        "lastname": last,
        "email": email,
        "tags": ["crm_preview", f"deal_type:{deal_type}"],
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.mautic_base_url}/api/contacts/new", json=payload, headers=headers,
            )
            resp.raise_for_status()
            contact_id = resp.json()["contact"]["id"]

            if settings.mautic_segment_id:
                seg_resp = await client.post(
                    f"{settings.mautic_base_url}/api/segments/{settings.mautic_segment_id}"
                    f"/contact/{contact_id}/add",
                    headers=headers,
                )
                seg_resp.raise_for_status()

        logger.info("mautic-push ok email=%s contact_id=%s", email, contact_id)
    except Exception:
        logger.exception("mautic-push failed email=%s", email)
