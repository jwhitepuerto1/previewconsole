"""GET/POST/PATCH /api/meetings, /api/meetings/{id}/action-items."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import InvestorTarget, Meeting, MeetingActionItem
from app.db.session import get_tenant_db
from app.services import suitecrm

router = APIRouter()

_READ_PERMS = ("read:own_raise", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:meetings", "*")


class MeetingOut(BaseModel):
    id: uuid.UUID
    investor_target_id: uuid.UUID | None
    meeting_type: str | None
    scheduled_at: datetime | None
    duration_minutes: int | None
    participants: list[str] | None
    location_or_link: str | None
    status: str | None
    outcome: str | None
    next_step: str | None
    next_step_date: date | None


class CreateMeetingRequest(BaseModel):
    investor_target_id: uuid.UUID
    meeting_type: str
    scheduled_at: datetime
    duration_minutes: int | None = None
    participants: list[str] | None = None
    location_or_link: str | None = None
    logged_by: str | None = None


class UpdateMeetingRequest(BaseModel):
    status: str | None = None
    outcome: str | None = None
    notes: str | None = None
    next_step: str | None = None
    next_step_date: date | None = None


def _to_out(m: Meeting) -> MeetingOut:
    return MeetingOut(
        id=m.id, investor_target_id=m.investor_target_id, meeting_type=m.meeting_type,
        scheduled_at=m.scheduled_at, duration_minutes=m.duration_minutes, participants=m.participants,
        location_or_link=m.location_or_link, status=m.status, outcome=m.outcome,
        next_step=m.next_step, next_step_date=m.next_step_date,
    )


@router.get("", response_model=list[MeetingOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_meetings(db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(select(Meeting).order_by(Meeting.scheduled_at))).scalars().all()
    return [_to_out(m) for m in rows]


@router.post("", response_model=MeetingOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def create_meeting(body: CreateMeetingRequest, db: AsyncSession = Depends(get_tenant_db)):
    meeting = Meeting(
        investor_target_id=body.investor_target_id, meeting_type=body.meeting_type,
        scheduled_at=body.scheduled_at, duration_minutes=body.duration_minutes,
        participants=body.participants, location_or_link=body.location_or_link,
        status="scheduled", logged_by=body.logged_by,
    )
    db.add(meeting)
    await db.commit()
    return _to_out(meeting)


@router.patch("/{meeting_id}", response_model=MeetingOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_meeting(meeting_id: uuid.UUID, body: UpdateMeetingRequest, db: AsyncSession = Depends(get_tenant_db)):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)
    await db.commit()

    if body.outcome and meeting.investor_target_id:
        target = await db.get(InvestorTarget, meeting.investor_target_id)
        if target and target.email:
            await suitecrm.log_activity(
                email=target.email,
                description=f"Meeting ({meeting.meeting_type}) outcome: {body.outcome}",
            )

    return _to_out(meeting)


class ActionItemOut(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID | None
    action: str | None
    assigned_to: str | None
    due_date: date | None
    completed: bool
    completed_at: datetime | None


class CreateActionItemRequest(BaseModel):
    action: str
    assigned_to: str | None = None
    due_date: date | None = None


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_action_items(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (
        await db.execute(select(MeetingActionItem).where(MeetingActionItem.meeting_id == meeting_id))
    ).scalars().all()
    return [
        ActionItemOut(
            id=a.id, meeting_id=a.meeting_id, action=a.action, assigned_to=a.assigned_to,
            due_date=a.due_date, completed=a.completed, completed_at=a.completed_at,
        )
        for a in rows
    ]


@router.post("/{meeting_id}/action-items", response_model=ActionItemOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def create_action_item(meeting_id: uuid.UUID, body: CreateActionItemRequest, db: AsyncSession = Depends(get_tenant_db)):
    item = MeetingActionItem(
        meeting_id=meeting_id, action=body.action, assigned_to=body.assigned_to, due_date=body.due_date,
    )
    db.add(item)
    await db.commit()
    return ActionItemOut(
        id=item.id, meeting_id=item.meeting_id, action=item.action, assigned_to=item.assigned_to,
        due_date=item.due_date, completed=item.completed, completed_at=item.completed_at,
    )
