"""
SuiteCRM API client (CLAUDE_CRM_MODULE.md section 13) — pushes investor
records and logs pipeline/meeting activity to SuiteCRM's Contact record.

Same best-effort shape as Mautic/Smartlead: no-op with a logged warning if
SUITECRM_URL/SUITECRM_API_KEY aren't set. Deliberately create-or-update by
email rather than persisting a suitecrm_contact_id back onto InvestorTarget
— unlike Campaign's smartlead_campaign_id/mautic_campaign_id (both already
in section 7's schema), there's no SuiteCRM-id column on investor_targets,
and this integration has zero real credentials to test a migration against
yet. If contact volume ever makes per-request search-by-email too slow,
that's the point to add the column, not before.

SUITECRM_API_KEY is assumed to already be a valid bearer/personal access
token for the target instance. Real SuiteCRM v8 deployments typically front
this with an OAuth2 password or client_credentials exchange first — that
handshake isn't implemented here since there's no real instance yet to
verify the exact flow/token lifetime against; wire it in the same place
Mautic's token refresh lives (_refresh_access_token) once there is one.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.suitecrm_url and settings.suitecrm_api_key)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.suitecrm_api_key}", "Content-Type": "application/vnd.api+json"}


async def _find_contact_id(client: httpx.AsyncClient, email: str) -> str | None:
    resp = await client.get(
        f"{settings.suitecrm_url}/Api/V8/module/Contacts",
        params={"filter[email1][eq]": email},
        headers=_headers(),
    )
    resp.raise_for_status()
    data = resp.json().get("data") or []
    return data[0]["id"] if data else None


async def push_contact(*, email: str, name: str, title: str | None, company: str | None) -> str | None:
    """Create-or-update by email. Returns the SuiteCRM contact id, or None
    if not configured/failed — best-effort, never raises."""
    if not is_configured():
        logger.warning("suitecrm-push-contact skipped: SUITECRM_* not configured")
        return None

    first, _, last = (name or "").strip().partition(" ")
    attributes = {"first_name": first, "last_name": last or first, "email1": email, "title": title, "account_name": company}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            contact_id = await _find_contact_id(client, email)
            body = {"data": {"type": "Contacts", "attributes": attributes}}
            if contact_id:
                body["data"]["id"] = contact_id
                resp = await client.patch(f"{settings.suitecrm_url}/Api/V8/module", json=body, headers=_headers())
            else:
                resp = await client.post(f"{settings.suitecrm_url}/Api/V8/module", json=body, headers=_headers())
            resp.raise_for_status()
            new_id = resp.json()["data"]["id"]
            logger.info("suitecrm-push-contact ok email=%s contact_id=%s", email, new_id)
            return new_id
    except Exception:
        logger.exception("suitecrm-push-contact failed email=%s", email)
        return None


async def log_activity(*, email: str, description: str) -> None:
    """Logs a Note against the contact found by email — pipeline movements
    and meeting outcomes (section 13's own sync description). Best-effort:
    finds-then-skips silently if the contact doesn't exist in SuiteCRM yet
    rather than creating an orphan note."""
    if not is_configured():
        logger.warning("suitecrm-log-activity skipped: SUITECRM_* not configured")
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            contact_id = await _find_contact_id(client, email)
            if not contact_id:
                logger.warning("suitecrm-log-activity skipped: no contact found for email=%s", email)
                return
            body = {
                "data": {
                    "type": "Notes",
                    "attributes": {"name": description[:255], "description": description},
                    "relationships": {"contacts": {"data": [{"type": "Contacts", "id": contact_id}]}},
                }
            }
            resp = await client.post(f"{settings.suitecrm_url}/Api/V8/module", json=body, headers=_headers())
            resp.raise_for_status()
            logger.info("suitecrm-log-activity ok email=%s contact_id=%s", email, contact_id)
    except Exception:
        logger.exception("suitecrm-log-activity failed email=%s", email)
