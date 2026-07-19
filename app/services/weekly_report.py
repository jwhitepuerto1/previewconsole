"""
Weekly report generation engine (CLAUDE_CRM_MODULE.md section 12).
Computes the four summary blocks from the tenant DB's own tables for the
7 days ending on `week_ending`; the three free-text fields
(key_activities/next_week_priorities/rep_commentary) are rep-written and
left blank here for api/routes/reports.py's PATCH to fill in — the spec is
explicit that the report is system-generated but rep-published, never
auto-published with system commentary standing in for a human's.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client_raise import (
    CampaignMetrics,
    EmailSequenceEvent,
    FundingEvent,
    FundingSummary,
    InvestorTarget,
    LinkedinTouchpoint,
    Meeting,
    PipelineHistory,
    PipelineRecord,
    WeeklyReport,
)

# Linear pipeline progression used to classify a stage move as forward or
# backward. "declined"/"on_hold" are side-exits, not a position on this line.
_STAGE_ORDER = [
    "prospect", "qualified", "engaged", "meeting_scheduled", "meeting_completed",
    "soft_committed", "committed", "onboarding", "funded",
]


async def _pipeline_summary(db: AsyncSession, week_start: datetime, week_end: datetime) -> dict:
    total = (await db.execute(select(func.count()).select_from(PipelineRecord))).scalar_one()
    by_stage_rows = (await db.execute(select(PipelineRecord.stage, func.count()).group_by(PipelineRecord.stage))).all()

    moves = (
        await db.execute(
            select(PipelineHistory.from_stage, PipelineHistory.to_stage)
            .where(PipelineHistory.moved_at >= week_start, PipelineHistory.moved_at < week_end)
        )
    ).all()
    forward = backward = declined_this_week = 0
    for from_stage, to_stage in moves:
        if to_stage == "declined":
            declined_this_week += 1
        if from_stage in _STAGE_ORDER and to_stage in _STAGE_ORDER:
            if _STAGE_ORDER.index(to_stage) > _STAGE_ORDER.index(from_stage):
                forward += 1
            elif _STAGE_ORDER.index(to_stage) < _STAGE_ORDER.index(from_stage):
                backward += 1

    new_count = (
        await db.execute(
            select(func.count()).select_from(InvestorTarget)
            .where(InvestorTarget.added_at >= week_start, InvestorTarget.added_at < week_end)
        )
    ).scalar_one()

    return {
        "total_in_pipeline": total,
        "by_stage": {stage: count for stage, count in by_stage_rows},
        "moved_forward_this_week": forward,
        "moved_backward_this_week": backward,
        "new_this_week": new_count,
        "removed_this_week": declined_this_week,
    }


async def _campaign_summary(db: AsyncSession, week_start: datetime, week_end: datetime) -> dict:
    metrics_rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(CampaignMetrics.sent_count), 0),
                func.coalesce(func.sum(CampaignMetrics.unsubscribe_count), 0),
            ).where(CampaignMetrics.metric_date >= week_start.date(), CampaignMetrics.metric_date < week_end.date())
        )
    ).one()
    emails_sent, unsubscribes = metrics_rows

    events = (
        await db.execute(
            select(EmailSequenceEvent.event_type, func.count())
            .where(EmailSequenceEvent.event_at >= week_start, EmailSequenceEvent.event_at < week_end)
            .group_by(EmailSequenceEvent.event_type)
        )
    ).all()
    event_counts = {t: c for t, c in events}
    sent = event_counts.get("sent", 0) or emails_sent
    opened = event_counts.get("opened", 0)
    replied = event_counts.get("replied", 0)

    linkedin_count = (
        await db.execute(
            select(func.count()).select_from(LinkedinTouchpoint)
            .where(LinkedinTouchpoint.sent_at >= week_start, LinkedinTouchpoint.sent_at < week_end)
        )
    ).scalar_one()

    return {
        "emails_sent": sent,
        "open_rate": round(opened / sent, 4) if sent else 0.0,
        "reply_rate": round(replied / sent, 4) if sent else 0.0,
        "positive_replies": replied,
        "unsubscribes": unsubscribes,
        "linkedin_touchpoints": linkedin_count,
    }


async def _meeting_summary(db: AsyncSession, week_start: datetime, week_end: datetime) -> dict:
    held = (
        await db.execute(
            select(func.count()).select_from(Meeting)
            .where(Meeting.status == "completed", Meeting.scheduled_at >= week_start, Meeting.scheduled_at < week_end)
        )
    ).scalar_one()
    scheduled_next_week = (
        await db.execute(
            select(func.count()).select_from(Meeting)
            .where(Meeting.scheduled_at >= week_end, Meeting.scheduled_at < week_end + timedelta(days=7))
        )
    ).scalar_one()
    positive = (
        await db.execute(
            select(func.count()).select_from(Meeting)
            .where(Meeting.outcome == "positive", Meeting.scheduled_at >= week_start, Meeting.scheduled_at < week_end)
        )
    ).scalar_one()
    follow_ups = (
        await db.execute(
            select(func.count()).select_from(Meeting)
            .where(Meeting.outcome == "follow_up_required", Meeting.scheduled_at >= week_start, Meeting.scheduled_at < week_end)
        )
    ).scalar_one()
    return {
        "meetings_held": held,
        "meetings_scheduled_next_week": scheduled_next_week,
        "positive_outcomes": positive,
        "follow_ups_required": follow_ups,
    }


async def _funding_summary(db: AsyncSession, week_start: datetime, week_end: datetime) -> dict:
    summary = (await db.execute(select(FundingSummary))).scalars().first()
    new_commitments = (
        await db.execute(
            select(func.count()).select_from(FundingEvent)
            .where(FundingEvent.created_at >= week_start, FundingEvent.created_at < week_end)
        )
    ).scalar_one()
    return {
        "raise_target": summary.raise_target if summary else None,
        "soft_committed": summary.soft_committed if summary else 0,
        "hard_committed": summary.hard_committed if summary else 0,
        "funded": summary.funded if summary else 0,
        "percent_of_target": summary.percent_raised if summary else 0.0,
        "new_commitments_this_week": new_commitments,
    }


async def generate_report(db: AsyncSession, week_ending: date) -> WeeklyReport:
    week_end = datetime.combine(week_ending, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    week_start = week_end - timedelta(days=7)

    report = WeeklyReport(
        report_week_ending=week_ending,
        generated_by="system",
        pipeline_summary=await _pipeline_summary(db, week_start, week_end),
        campaign_summary=await _campaign_summary(db, week_start, week_end),
        meeting_summary=await _meeting_summary(db, week_start, week_end),
        funding_summary=await _funding_summary(db, week_start, week_end),
        status="draft",
    )
    db.add(report)
    await db.commit()
    return report
