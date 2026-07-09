"""
Preview mode routes — CLAUDE_CRM_MODULE.md section 10.
POST /register is the only unauthenticated route (see middleware/auth.py's
OPEN_PATHS). Every other route requires a valid, non-expired preview JWT and
reads from whichever preview database that token resolved to
(middleware/auth.py sets request.state.client_db_url; db/session.py's
get_tenant_db() picks it up) — routes never decode a token or choose a
database themselves.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_preview_token
from app.db.models.client_raise import (
    CampaignMetrics,
    Campaign,
    DataRoomAccessLog,
    DataRoomDocument,
    FundingEvent,
    FundingSummary,
    InvestorTarget,
    Meeting,
    PipelineRecord,
    RaiseConfig,
    WeeklyReport,
)
from app.db.models.platform import PlatformAuditLog
from app.db.session import get_platform_db, get_tenant_db

router = APIRouter()

PROFILE_DISPLAY_NAMES = {
    "ias_crm_preview_meridian": "Meridian Capital Partners",
    "ias_crm_preview_cornerstone": "Cornerstone Credit Fund I",
    "ias_crm_preview_elevation": "Elevation Income REIT",
}


def require_preview(request: Request) -> None:
    if not request.state.is_preview or not request.state.client_db_url:
        raise HTTPException(status_code=401, detail="A valid preview token is required.")


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    deal_type: str
    raise_target: int


class RegisterResponse(BaseModel):
    token: str
    profile_db: str
    profile_name: str


@router.post("/register", response_model=RegisterResponse)
async def register(body: RegisterRequest, platform_db: AsyncSession = Depends(get_platform_db)):
    profile_db = settings.preview_db_map.get(body.deal_type, settings.preview_db_map["other"])
    profile_name = PROFILE_DISPLAY_NAMES[profile_db]

    token = create_preview_token(
        name=body.name,
        email=body.email,
        deal_type=body.deal_type,
        raise_target=body.raise_target,
        client_db=profile_db,
    )

    platform_db.add(PlatformAuditLog(
        user_id=None,
        user_role="preview",
        client_id=None,  # no real platform_accounts row for preview sessions
        action="preview_registered",
        entity_type="preview_session",
        entity_id=None,
        payload={
            "name": body.name, "email": body.email, "deal_type": body.deal_type,
            "raise_target": body.raise_target, "profile_db": profile_db,
        },
    ))
    await platform_db.commit()

    return RegisterResponse(token=token, profile_db=profile_db, profile_name=profile_name)


# ── Track (page visits / CTA clicks — business rule 8) ─────────────────────────

class TrackRequest(BaseModel):
    event_type: str  # page_visit | cta_click
    detail: str | None = None


@router.post("/track")
async def track(
    body: TrackRequest,
    request: Request,
    _: None = Depends(require_preview),
    platform_db: AsyncSession = Depends(get_platform_db),
):
    claims = request.state.claims
    platform_db.add(PlatformAuditLog(
        user_id=None,
        user_role="preview",
        client_id=None,
        action=f"preview_{body.event_type}",
        entity_type="preview_session",
        entity_id=None,
        payload={"detail": body.detail, "profile_db": claims.get("client_db"), "sub": claims.get("sub")},
    ))
    await platform_db.commit()
    return {"status": "logged"}


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(_: None = Depends(require_preview), db: AsyncSession = Depends(get_tenant_db)):
    config = (await db.execute(select(RaiseConfig))).scalars().first()
    funding = (await db.execute(select(FundingSummary))).scalars().first()
    target_count = (await db.execute(select(func.count()).select_from(InvestorTarget))).scalar_one()

    stage_rows = (await db.execute(
        select(PipelineRecord.stage, func.count()).group_by(PipelineRecord.stage)
    )).all()
    by_stage = {stage: count for stage, count in stage_rows}

    days_active = None
    if config and config.launch_date:
        days_active = (date.today() - config.launch_date).days

    return {
        "raise_name": config.raise_name if config else None,
        "deal_type": config.deal_type if config else None,
        "raise_target": config.raise_target if config else None,
        "days_active": days_active,
        "status": config.status if config else None,
        "investor_count": target_count,
        "pipeline_by_stage": by_stage,
        "funding": {
            "soft_committed": funding.soft_committed if funding else 0,
            "hard_committed": funding.hard_committed if funding else 0,
            "funded": funding.funded if funding else 0,
            "percent_raised": funding.percent_raised if funding else 0,
        },
    }


# ── Pipeline ─────────────────────────────────────────────────────────────────

@router.get("/pipeline")
async def pipeline(_: None = Depends(require_preview), db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(
        select(InvestorTarget, PipelineRecord)
        .join(PipelineRecord, PipelineRecord.investor_target_id == InvestorTarget.id)
    )).all()

    return {
        "investors": [
            {
                "id": str(target.id),
                "full_name": target.full_name,
                "company": target.company,
                "title": target.title,
                "investor_type": target.investor_type,
                "fit_score": target.fit_score,
                "stage": record.stage,
                "days_in_stage": record.days_in_stage,
            }
            for target, record in rows
        ]
    }


# ── Campaigns ────────────────────────────────────────────────────────────────

@router.get("/campaigns")
async def campaigns(_: None = Depends(require_preview), db: AsyncSession = Depends(get_tenant_db)):
    campaign = (await db.execute(select(Campaign))).scalars().first()
    metrics_rows = (await db.execute(
        select(CampaignMetrics).order_by(CampaignMetrics.metric_date)
    )).scalars().all()
    meeting_count = (await db.execute(select(func.count()).select_from(Meeting))).scalar_one()

    totals = {
        "sent": sum(m.sent_count or 0 for m in metrics_rows),
        "opened": sum(m.open_count or 0 for m in metrics_rows),
        "replied": sum(m.reply_count or 0 for m in metrics_rows),
    }
    open_rate = round(totals["opened"] / totals["sent"] * 100, 1) if totals["sent"] else 0
    reply_rate = round(totals["replied"] / totals["sent"] * 100, 1) if totals["sent"] else 0

    return {
        "campaign_name": campaign.campaign_name if campaign else None,
        "channel": campaign.channel if campaign else None,
        "status": campaign.status if campaign else None,
        "open_rate": open_rate,
        "reply_rate": reply_rate,
        "meetings_scheduled": meeting_count,
        "weekly_metrics": [
            {
                "week_ending": m.metric_date.isoformat() if m.metric_date else None,
                "sent": m.sent_count, "opened": m.open_count, "replied": m.reply_count,
            }
            for m in metrics_rows
        ],
    }


# ── Data room ────────────────────────────────────────────────────────────────

@router.get("/data-room")
async def data_room(_: None = Depends(require_preview), db: AsyncSession = Depends(get_tenant_db)):
    docs = (await db.execute(select(DataRoomDocument).where(DataRoomDocument.is_active))).scalars().all()

    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    views_this_week = (await db.execute(
        select(func.count()).select_from(DataRoomAccessLog)
        .where(DataRoomAccessLog.accessed_at >= one_week_ago)
    )).scalar_one()

    return {
        "documents": [
            {
                "id": str(d.id), "name": d.document_name, "type": d.document_type,
                "access_level": d.access_level, "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in docs
        ],
        "views_this_week": views_this_week,
    }


# ── Weekly report ────────────────────────────────────────────────────────────

@router.get("/reports")
async def reports(_: None = Depends(require_preview), db: AsyncSession = Depends(get_tenant_db)):
    report = (await db.execute(
        select(WeeklyReport).where(WeeklyReport.status == "published")
        .order_by(WeeklyReport.report_week_ending.desc())
    )).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="No published weekly report found.")

    return {
        "report_week_ending": report.report_week_ending.isoformat() if report.report_week_ending else None,
        "pipeline_summary": report.pipeline_summary,
        "campaign_summary": report.campaign_summary,
        "meeting_summary": report.meeting_summary,
        "funding_summary": report.funding_summary,
        "key_activities": report.key_activities,
        "next_week_priorities": report.next_week_priorities,
        "rep_commentary": report.rep_commentary,
    }


# ── Funding ──────────────────────────────────────────────────────────────────

@router.get("/funding")
async def funding(_: None = Depends(require_preview), db: AsyncSession = Depends(get_tenant_db)):
    summary = (await db.execute(select(FundingSummary))).scalars().first()
    events = (await db.execute(select(FundingEvent).order_by(FundingEvent.event_date.desc()))).scalars().all()

    return {
        "summary": {
            "raise_target": summary.raise_target if summary else None,
            "soft_committed": summary.soft_committed if summary else 0,
            "hard_committed": summary.hard_committed if summary else 0,
            "funded": summary.funded if summary else 0,
            "investor_count_soft": summary.investor_count_soft if summary else 0,
            "investor_count_funded": summary.investor_count_funded if summary else 0,
            "percent_raised": summary.percent_raised if summary else 0,
        },
        "events": [
            {
                "event_type": e.event_type, "amount": e.amount,
                "event_date": e.event_date.isoformat() if e.event_date else None,
            }
            for e in events
        ],
    }
