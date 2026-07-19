"""
North Capital API client (CLAUDE_CRM_MODULE.md section 13) — KYC initiation,
accreditation verification, and subscription document management.

Same best-effort shape as the other integrations: no-op with a logged
warning if NORTH_CAPITAL_* isn't set. Status updates arrive via webhook
(api/routes/onboarding.py's /webhooks/north-capital/{client_id}), not
polling — initiate_kyc() only kicks the process off and returns North
Capital's own reference id, stored on OnboardingRecord.north_capital_reference
(already in section 7's schema — no migration needed).
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.north_capital_base_url and settings.north_capital_api_key)


async def initiate_kyc(*, investor_name: str, investor_email: str, investment_amount: int | None) -> str | None:
    """Returns North Capital's own reference id for this onboarding, or None
    if not configured/failed."""
    if not is_configured():
        logger.warning("north-capital-initiate skipped: NORTH_CAPITAL_* not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.north_capital_base_url}/onboarding",
                headers={"Authorization": f"Bearer {settings.north_capital_api_key}"},
                json={
                    "environment": settings.north_capital_environment,
                    "investor_name": investor_name,
                    "investor_email": investor_email,
                    "investment_amount": investment_amount,
                },
            )
            resp.raise_for_status()
            reference = resp.json()["reference"]
            logger.info("north-capital-initiate ok email=%s reference=%s", investor_email, reference)
            return reference
    except Exception:
        logger.exception("north-capital-initiate failed email=%s", investor_email)
        return None
