"""
Smartlead API client — campaign creation and contact enrollment for the
Phase 2 campaign workflow (CLAUDE_CRM_MODULE.md section 13).

Same best-effort shape as app/integrations/mautic.py's push_lead: every call
here is optional infrastructure a client campaign can run without. If
SMARTLEAD_API_KEY isn't set, every function returns None/no-ops instead of
raising, so campaigns.py's routes stay usable (as local-only records) in
environments that haven't wired up Smartlead yet.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.smartlead_api_key)


async def create_campaign(campaign_name: str) -> str | None:
    """Returns the new Smartlead campaign id, or None if not configured/failed."""
    if not is_configured():
        logger.warning("smartlead-create-campaign skipped: SMARTLEAD_API_KEY not configured")
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.smartlead_base_url}/campaigns/create",
                params={"api_key": settings.smartlead_api_key},
                json={"name": campaign_name},
            )
            resp.raise_for_status()
            return str(resp.json()["id"])
    except Exception:
        logger.exception("smartlead-create-campaign failed name=%s", campaign_name)
        return None


async def add_lead(smartlead_campaign_id: str, *, email: str, first_name: str, last_name: str) -> bool:
    if not is_configured():
        logger.warning("smartlead-add-lead skipped: SMARTLEAD_API_KEY not configured")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.smartlead_base_url}/campaigns/{smartlead_campaign_id}/leads",
                params={"api_key": settings.smartlead_api_key},
                json={"lead_list": [{"email": email, "first_name": first_name, "last_name": last_name}]},
            )
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("smartlead-add-lead failed campaign=%s email=%s", smartlead_campaign_id, email)
        return False


async def set_campaign_status(smartlead_campaign_id: str, status: str) -> bool:
    """status: PAUSED | START — Smartlead's own campaign-status vocabulary."""
    if not is_configured():
        logger.warning("smartlead-set-status skipped: SMARTLEAD_API_KEY not configured")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.smartlead_base_url}/campaigns/{smartlead_campaign_id}/status",
                params={"api_key": settings.smartlead_api_key},
                json={"status": status},
            )
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("smartlead-set-status failed campaign=%s status=%s", smartlead_campaign_id, status)
        return False
