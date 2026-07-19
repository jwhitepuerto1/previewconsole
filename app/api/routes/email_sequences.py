"""
GET /api/email-events/{target_id} — per-investor email activity, tenant-DB
scoped like every other real route.

POST /api/email-events/sync/{client_id} — Smartlead's webhook receiver.
Deliberately NOT behind JWT auth (Smartlead can't hold a per-client bearer
token) — added to AuthMiddleware.OPEN_PATHS instead and guarded by a shared
secret header, the same shape as a typical webhook signature check. The
client_id is in the path because campaigns/leads live in that client's own
database — Smartlead's payload only knows its own campaign id, not which of
our per-client databases it belongs to, so we have to be told which one this
is for at the URL level (that's what's registered as the webhook URL for a
given campaign).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.config import settings
from app.db.models.client_raise import Campaign, EmailSequenceEvent, InvestorTarget
from app.db.models.platform import PlatformAccount
from app.db.session import get_engine, get_platform_db, get_tenant_db

router = APIRouter()

_READ_PERMS = ("read:campaigns", "read:all_assigned_clients", "*")


@router.get("/{target_id}", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def target_email_activity(target_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (
        await db.execute(
            select(EmailSequenceEvent)
            .where(EmailSequenceEvent.investor_target_id == target_id)
            .order_by(EmailSequenceEvent.event_at)
        )
    ).scalars().all()
    return {
        "events": [
            {
                "campaign_id": str(e.campaign_id) if e.campaign_id else None,
                "event_type": e.event_type,
                "event_at": e.event_at.isoformat() if e.event_at else None,
                "subject_line": e.subject_line,
                "sequence_step": e.sequence_step,
            }
            for e in rows
        ]
    }


class SmartleadWebhookEvent(BaseModel):
    smartlead_campaign_id: str
    lead_email: str
    event_type: str  # sent | opened | clicked | replied | bounced | unsubscribed
    event_at: str | None = None
    subject_line: str | None = None
    sequence_step: int | None = None
    smartlead_event_id: str | None = None


@router.post("/sync/{client_id}")
async def sync_smartlead_webhook(
    client_id: uuid.UUID,
    body: SmartleadWebhookEvent,
    x_webhook_secret: str | None = Header(default=None),
    platform_db: AsyncSession = Depends(get_platform_db),
):
    if not settings.smartlead_webhook_secret or x_webhook_secret != settings.smartlead_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing webhook secret.")

    account = (
        await platform_db.execute(select(PlatformAccount).where(PlatformAccount.id == client_id))
    ).scalar_one_or_none()
    if not account or not account.client_db_url:
        raise HTTPException(status_code=404, detail="Client account not found or not provisioned.")

    _, sessionmaker = get_engine(account.client_db_url)
    async with sessionmaker() as client_db:
        campaign = (
            await client_db.execute(
                select(Campaign).where(Campaign.smartlead_campaign_id == body.smartlead_campaign_id)
            )
        ).scalar_one_or_none()

        target = (
            await client_db.execute(select(InvestorTarget).where(InvestorTarget.email == body.lead_email))
        ).scalar_one_or_none()

        client_db.add(EmailSequenceEvent(
            investor_target_id=target.id if target else None,
            campaign_id=campaign.id if campaign else None,
            event_type=body.event_type,
            event_at=body.event_at,
            subject_line=body.subject_line,
            sequence_step=body.sequence_step,
            smartlead_event_id=body.smartlead_event_id,
            raw_payload=body.model_dump(),
        ))
        await client_db.commit()

    return {"status": "ok"}
