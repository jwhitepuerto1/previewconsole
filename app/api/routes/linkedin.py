"""GET /api/linkedin/{target_id}, POST/PATCH /api/linkedin — touchpoint log."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import LinkedinTouchpoint
from app.db.session import get_tenant_db

router = APIRouter()

_READ_PERMS = ("read:own_raise", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:pipeline", "*")  # spec has no dedicated write:linkedin — rides with write:pipeline


class TouchpointOut(BaseModel):
    id: uuid.UUID
    investor_target_id: uuid.UUID | None
    touchpoint_type: str | None
    content_summary: str | None
    sent_by: str | None
    sent_at: datetime | None
    response_received: bool
    response_summary: str | None
    response_at: datetime | None


class CreateTouchpointRequest(BaseModel):
    investor_target_id: uuid.UUID
    touchpoint_type: str
    content_summary: str | None = None
    sent_by: str | None = None


class UpdateTouchpointRequest(BaseModel):
    response_received: bool | None = None
    response_summary: str | None = None


def _to_out(t: LinkedinTouchpoint) -> TouchpointOut:
    return TouchpointOut(
        id=t.id, investor_target_id=t.investor_target_id, touchpoint_type=t.touchpoint_type,
        content_summary=t.content_summary, sent_by=t.sent_by, sent_at=t.sent_at,
        response_received=t.response_received, response_summary=t.response_summary, response_at=t.response_at,
    )


@router.get("/{target_id}", response_model=list[TouchpointOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_touchpoints(target_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (
        await db.execute(
            select(LinkedinTouchpoint)
            .where(LinkedinTouchpoint.investor_target_id == target_id)
            .order_by(LinkedinTouchpoint.sent_at)
        )
    ).scalars().all()
    return [_to_out(t) for t in rows]


@router.post("", response_model=TouchpointOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def create_touchpoint(body: CreateTouchpointRequest, db: AsyncSession = Depends(get_tenant_db)):
    touchpoint = LinkedinTouchpoint(
        investor_target_id=body.investor_target_id,
        touchpoint_type=body.touchpoint_type,
        content_summary=body.content_summary,
        sent_by=body.sent_by,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(touchpoint)
    await db.commit()
    return _to_out(touchpoint)


@router.patch("/{touchpoint_id}", response_model=TouchpointOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_touchpoint(touchpoint_id: uuid.UUID, body: UpdateTouchpointRequest, db: AsyncSession = Depends(get_tenant_db)):
    touchpoint = await db.get(LinkedinTouchpoint, touchpoint_id)
    if not touchpoint:
        raise HTTPException(status_code=404, detail="Touchpoint not found.")
    if body.response_received is not None:
        touchpoint.response_received = body.response_received
        touchpoint.response_at = datetime.now(timezone.utc)
    if body.response_summary is not None:
        touchpoint.response_summary = body.response_summary
    await db.commit()
    return _to_out(touchpoint)
