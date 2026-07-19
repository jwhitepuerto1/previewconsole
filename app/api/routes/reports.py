"""GET /api/reports, POST /api/reports/generate, PATCH + /publish."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import WeeklyReport
from app.db.session import get_tenant_db
from app.services.weekly_report import generate_report

router = APIRouter()

_READ_PERMS = ("read:reports", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:reports", "*")


class ReportOut(BaseModel):
    id: uuid.UUID
    report_week_ending: date | None
    generated_at: datetime
    generated_by: str | None
    pipeline_summary: dict | None
    campaign_summary: dict | None
    meeting_summary: dict | None
    funding_summary: dict | None
    key_activities: str | None
    next_week_priorities: str | None
    rep_commentary: str | None
    status: str | None
    published_at: datetime | None


class GenerateReportRequest(BaseModel):
    week_ending: date | None = None  # defaults to today


class UpdateReportRequest(BaseModel):
    key_activities: str | None = None
    next_week_priorities: str | None = None
    rep_commentary: str | None = None


def _to_out(r: WeeklyReport) -> ReportOut:
    return ReportOut(
        id=r.id, report_week_ending=r.report_week_ending, generated_at=r.generated_at,
        generated_by=r.generated_by, pipeline_summary=r.pipeline_summary, campaign_summary=r.campaign_summary,
        meeting_summary=r.meeting_summary, funding_summary=r.funding_summary, key_activities=r.key_activities,
        next_week_priorities=r.next_week_priorities, rep_commentary=r.rep_commentary,
        status=r.status, published_at=r.published_at,
    )


@router.get("", response_model=list[ReportOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_reports(db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(select(WeeklyReport).order_by(WeeklyReport.report_week_ending.desc()))).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/{report_id}", response_model=ReportOut, dependencies=[Depends(require_permission(*_READ_PERMS))])
async def get_report(report_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    report = await db.get(WeeklyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _to_out(report)


@router.post("/generate", response_model=ReportOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def trigger_generate(body: GenerateReportRequest, db: AsyncSession = Depends(get_tenant_db)):
    report = await generate_report(db, body.week_ending or date.today())
    return _to_out(report)


@router.patch("/{report_id}", response_model=ReportOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_report(report_id: uuid.UUID, body: UpdateReportRequest, db: AsyncSession = Depends(get_tenant_db)):
    report = await db.get(WeeklyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.status == "published":
        raise HTTPException(status_code=409, detail="Cannot edit a published report.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    await db.commit()
    return _to_out(report)


@router.post("/{report_id}/publish", response_model=ReportOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def publish_report(report_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    report = await db.get(WeeklyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    report.status = "published"
    report.published_at = datetime.now(timezone.utc)
    await db.commit()
    return _to_out(report)
