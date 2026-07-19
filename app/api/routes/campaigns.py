"""
GET/POST/PATCH /api/campaigns, /launch, /pause, /metrics, /activity.
Per the Section 5 permission matrix, only support_manager (and cc_admin's
"*") have write:campaigns — client roles are read-only here, matching the
spec's rep-managed campaign model.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import Campaign, CampaignMetrics, EmailSequenceEvent, InvestorTarget
from app.db.session import get_tenant_db
from app.services import smartlead

router = APIRouter()

_READ_PERMS = ("read:campaigns", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:campaigns", "*")


class CampaignOut(BaseModel):
    id: uuid.UUID
    campaign_name: str | None
    channel: str | None
    smartlead_campaign_id: str | None
    status: str | None
    start_date: date | None
    end_date: date | None
    target_count: int | None


class CreateCampaignRequest(BaseModel):
    campaign_name: str
    channel: str = "email"
    target_count: int | None = None


class UpdateCampaignRequest(BaseModel):
    campaign_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    target_count: int | None = None


def _to_out(c: Campaign) -> CampaignOut:
    return CampaignOut(
        id=c.id, campaign_name=c.campaign_name, channel=c.channel,
        smartlead_campaign_id=c.smartlead_campaign_id, status=c.status,
        start_date=c.start_date, end_date=c.end_date, target_count=c.target_count,
    )


async def _get_or_404(db: AsyncSession, campaign_id: uuid.UUID) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.get("", response_model=list[CampaignOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_campaigns(db: AsyncSession = Depends(get_tenant_db)):
    campaigns = (await db.execute(select(Campaign))).scalars().all()
    return [_to_out(c) for c in campaigns]


@router.post("", response_model=CampaignOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def create_campaign(body: CreateCampaignRequest, db: AsyncSession = Depends(get_tenant_db)):
    campaign = Campaign(
        campaign_name=body.campaign_name, channel=body.channel,
        target_count=body.target_count, status="draft",
    )
    db.add(campaign)
    await db.commit()
    return _to_out(campaign)


@router.patch("/{campaign_id}", response_model=CampaignOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_campaign(campaign_id: uuid.UUID, body: UpdateCampaignRequest, db: AsyncSession = Depends(get_tenant_db)):
    campaign = await _get_or_404(db, campaign_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    await db.commit()
    return _to_out(campaign)


@router.post("/{campaign_id}/launch", response_model=CampaignOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def launch_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """Creates the campaign in Smartlead (if configured) and enrolls every
    active investor target as a lead. Best-effort — a Smartlead outage
    never blocks the campaign from being marked active locally."""
    campaign = await _get_or_404(db, campaign_id)

    if not campaign.smartlead_campaign_id:
        smartlead_id = await smartlead.create_campaign(campaign.campaign_name or f"campaign-{campaign_id}")
        if smartlead_id:
            campaign.smartlead_campaign_id = smartlead_id

    if campaign.smartlead_campaign_id:
        targets = (await db.execute(select(InvestorTarget).where(InvestorTarget.status == "active"))).scalars().all()
        for target in targets:
            if not target.email:
                continue
            first, _, last = (target.full_name or "").strip().partition(" ")
            await smartlead.add_lead(campaign.smartlead_campaign_id, email=target.email, first_name=first, last_name=last)

    campaign.status = "active"
    await db.commit()
    return _to_out(campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def pause_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    campaign = await _get_or_404(db, campaign_id)
    if campaign.smartlead_campaign_id:
        await smartlead.set_campaign_status(campaign.smartlead_campaign_id, "PAUSED")
    campaign.status = "paused"
    await db.commit()
    return _to_out(campaign)


@router.get("/{campaign_id}/metrics", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def campaign_metrics(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    await _get_or_404(db, campaign_id)
    rows = (
        await db.execute(
            select(CampaignMetrics).where(CampaignMetrics.campaign_id == campaign_id).order_by(CampaignMetrics.metric_date)
        )
    ).scalars().all()
    return {
        "metrics": [
            {
                "metric_date": m.metric_date.isoformat() if m.metric_date else None,
                "sent_count": m.sent_count, "delivered_count": m.delivered_count,
                "open_count": m.open_count, "click_count": m.click_count,
                "reply_count": m.reply_count, "bounce_count": m.bounce_count,
                "unsubscribe_count": m.unsubscribe_count,
                "open_rate": m.open_rate, "reply_rate": m.reply_rate,
            }
            for m in rows
        ]
    }


@router.get("/{campaign_id}/activity", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def campaign_activity(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    await _get_or_404(db, campaign_id)
    rows = (
        await db.execute(
            select(EmailSequenceEvent).where(EmailSequenceEvent.campaign_id == campaign_id).order_by(EmailSequenceEvent.event_at)
        )
    ).scalars().all()
    return {
        "events": [
            {
                "investor_target_id": str(e.investor_target_id) if e.investor_target_id else None,
                "event_type": e.event_type,
                "event_at": e.event_at.isoformat() if e.event_at else None,
                "subject_line": e.subject_line,
                "sequence_step": e.sequence_step,
            }
            for e in rows
        ]
    }
