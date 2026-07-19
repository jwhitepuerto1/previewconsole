"""GET /api/alerts/stream (SSE), /api/alerts, PATCH .../read, POST mark-all-read."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import RaiseAlert
from app.db.session import get_tenant_db
from app.services.alert_dispatcher import subscribe, unsubscribe

router = APIRouter()

_READ_PERMS = ("read:alerts", "read:own_raise", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:alerts", "*")


@router.get("/stream")
async def alert_stream(request: Request):
    client_id = request.state.client_id
    if not client_id:
        raise HTTPException(status_code=400, detail="No client context for this token.")

    queue = subscribe(client_id)

    async def event_source():
        try:
            # Sent immediately on connect, before the queue can possibly miss
            # anything — lets any client (this stream's own test, or the real
            # UI) know the subscription is live rather than inferring it from
            # silence. publish() only reaches queues that already exist, so
            # without this a client has no way to know it's safe to act on
            # something that triggers an alert.
            yield f"data: {json.dumps({'type': 'ready'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    alert = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(alert)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe(client_id, queue)

    return StreamingResponse(event_source(), media_type="text/event-stream")


class AlertOut(BaseModel):
    id: uuid.UUID
    alert_type: str | None
    severity: str | None
    title: str | None
    message: str | None
    related_investor_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


def _to_out(a: RaiseAlert) -> AlertOut:
    return AlertOut(
        id=a.id, alert_type=a.alert_type, severity=a.severity, title=a.title, message=a.message,
        related_investor_id=a.related_investor_id, is_read=a.is_read, created_at=a.created_at,
    )


@router.get("", response_model=list[AlertOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_alerts(db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(select(RaiseAlert).order_by(RaiseAlert.created_at.desc()))).scalars().all()
    return [_to_out(a) for a in rows]


@router.patch("/{alert_id}/read", response_model=AlertOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def mark_read(alert_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    alert = await db.get(RaiseAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    claims = request.state.claims or {}
    alert.is_read = True
    alert.read_by = claims.get("email", "unknown")
    alert.read_at = datetime.now(timezone.utc)
    await db.commit()
    return _to_out(alert)


@router.post("/mark-all-read", dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def mark_all_read(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    claims = request.state.claims or {}
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(RaiseAlert)
        .where(RaiseAlert.is_read.is_(False))
        .values(is_read=True, read_by=claims.get("email", "unknown"), read_at=now)
    )
    await db.commit()
    return {"marked_read": result.rowcount}
