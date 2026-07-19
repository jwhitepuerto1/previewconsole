"""
Writes rep_activity_log rows (per-client table, section 7) — the raw feed
the support dashboard's "recent activity" and future engagement scoring
read from. A thin helper rather than instrumenting every write route:
wired into the handful of actions most indicative of a rep actually working
a raise (pipeline moves, meetings, funding events) as concrete examples;
extend to other routes the same way as the support dashboard's needs grow.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client_raise import RepActivityLog


async def log_rep_activity(
    db: AsyncSession,
    *,
    rep_user_id: uuid.UUID | str | None,
    activity_type: str,
    description: str,
    investor_target_id: uuid.UUID | None = None,
) -> None:
    if not rep_user_id:
        return
    db.add(RepActivityLog(
        rep_user_id=uuid.UUID(str(rep_user_id)),
        activity_type=activity_type,
        description=description,
        investor_target_id=investor_target_id,
    ))
