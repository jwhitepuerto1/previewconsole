"""
GET /api/funding/summary, GET/POST/PATCH /api/funding/events.
Business rule 5 (section 17): funding totals update in real-time on every
funding event — no manual reconciliation. _apply_to_summary is that single
recomputation point; every write path (create, and undo on delete/edit)
must go through it so the summary can never drift from the event log.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import FundingEvent, FundingSummary, InvestorTarget, RaiseConfig
from app.db.session import get_tenant_db
from app.services.alert_dispatcher import create_alert

router = APIRouter()

_READ_PERMS = ("read:funding", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:funding", "*")

# event_type -> (summary bucket field, sign) this event moves. wire_sent/
# wire_received are intermediate steps with no dedicated summary bucket in
# section 6's schema, so they're logged but don't move a total.
_BUCKET_MOVES: dict[str, tuple[str, int]] = {
    "soft_commit": ("soft_committed", 1),
    "hard_commit": ("hard_committed", 1),
    "funded": ("funded", 1),
    "returned": ("funded", -1),
}


async def _get_or_create_summary(db: AsyncSession) -> FundingSummary:
    summary = (await db.execute(select(FundingSummary))).scalars().first()
    if summary is None:
        config = (await db.execute(select(RaiseConfig))).scalars().first()
        summary = FundingSummary(raise_target=config.raise_target if config else None)
        db.add(summary)
        await db.flush()
    return summary


async def _apply_event_to_summary(db: AsyncSession, event: FundingEvent) -> None:
    summary = await _get_or_create_summary(db)
    move = _BUCKET_MOVES.get(event.event_type)
    if move:
        field, sign = move
        setattr(summary, field, getattr(summary, field) + sign * (event.amount or 0))
        if event.event_type == "funded":
            summary.investor_count_funded += 1
        elif event.event_type == "returned":
            summary.investor_count_funded = max(0, summary.investor_count_funded - 1)
    if summary.raise_target:
        summary.percent_raised = round(summary.funded / summary.raise_target, 4)


class FundingEventOut(BaseModel):
    id: uuid.UUID
    investor_target_id: uuid.UUID | None
    event_type: str | None
    amount: int | None
    event_date: date | None
    notes: str | None


class CreateFundingEventRequest(BaseModel):
    investor_target_id: uuid.UUID
    event_type: str
    amount: int
    event_date: date | None = None
    notes: str | None = None
    logged_by: str | None = None


def _to_out(e: FundingEvent) -> FundingEventOut:
    return FundingEventOut(
        id=e.id, investor_target_id=e.investor_target_id, event_type=e.event_type,
        amount=e.amount, event_date=e.event_date, notes=e.notes,
    )


@router.get("/summary", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def funding_summary(db: AsyncSession = Depends(get_tenant_db)):
    summary = await _get_or_create_summary(db)
    await db.commit()
    return {
        "raise_target": summary.raise_target,
        "soft_committed": summary.soft_committed,
        "hard_committed": summary.hard_committed,
        "funded": summary.funded,
        "investor_count_soft": summary.investor_count_soft,
        "investor_count_funded": summary.investor_count_funded,
        "percent_raised": summary.percent_raised,
    }


@router.get("/events", response_model=list[FundingEventOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_events(db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(select(FundingEvent).order_by(FundingEvent.created_at.desc()))).scalars().all()
    return [_to_out(e) for e in rows]


@router.post("/events", response_model=FundingEventOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def create_event(body: CreateFundingEventRequest, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    event = FundingEvent(
        investor_target_id=body.investor_target_id, event_type=body.event_type, amount=body.amount,
        event_date=body.event_date, notes=body.notes, logged_by=body.logged_by,
    )
    db.add(event)
    await db.flush()
    await _apply_event_to_summary(db, event)
    await db.commit()

    if request.state.client_id:
        target = await db.get(InvestorTarget, body.investor_target_id)
        await create_alert(
            db, request.state.client_id,
            alert_type="funding_event", severity="info",
            title="Funding event",
            message=f"{target.full_name if target else 'An investor'} committed ${body.amount:,}",
            related_investor_id=body.investor_target_id,
        )

    return _to_out(event)


class UpdateFundingEventRequest(BaseModel):
    notes: str | None = None


@router.patch("/events/{event_id}", response_model=FundingEventOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_event(event_id: uuid.UUID, body: UpdateFundingEventRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Notes-only edit — event_type/amount are immutable once summary totals
    have incorporated them (business rule 5 requires the summary to always
    match the log; correcting a mis-entered event means recording an
    offsetting 'returned' event, not silently rewriting history)."""
    event = await db.get(FundingEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Funding event not found.")
    if body.notes is not None:
        event.notes = body.notes
    await db.commit()
    return _to_out(event)
