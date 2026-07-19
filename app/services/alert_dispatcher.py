"""
In-process SSE fan-out for raise alerts (CLAUDE_CRM_MODULE.md sections 3, 11).
Single-process asyncio pub/sub, matching the spec's own "asyncio task queue"
choice for background jobs — no external broker. Each connected browser tab
holds one asyncio.Queue; create_alert() both persists the RaiseAlert row
(so GET /api/alerts/history and a late-connecting tab still see it) and
pushes it live to every currently-subscribed queue for that client.

Keyed by request.state.client_id (a client's own id, or the acting client id
support_manager/cc_admin resolved via X-Acting-Client-Id) — this is a
per-client fan-out, never global, so one client's browser tab can never
receive another client's alerts.
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client_raise import RaiseAlert

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)


def subscribe(client_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers[client_id].add(queue)
    return queue


def unsubscribe(client_id: str, queue: asyncio.Queue) -> None:
    _subscribers[client_id].discard(queue)


async def create_alert(
    db: AsyncSession,
    client_id: str,
    *,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    related_investor_id: uuid.UUID | None = None,
) -> RaiseAlert:
    alert = RaiseAlert(
        alert_type=alert_type, severity=severity, title=title, message=message,
        related_investor_id=related_investor_id,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    payload = {
        "id": str(alert.id), "alert_type": alert.alert_type, "severity": alert.severity,
        "title": alert.title, "message": alert.message,
        "related_investor_id": str(alert.related_investor_id) if alert.related_investor_id else None,
        "created_at": alert.created_at.isoformat(),
    }
    for queue in list(_subscribers.get(client_id, ())):
        queue.put_nowait(payload)

    return alert
