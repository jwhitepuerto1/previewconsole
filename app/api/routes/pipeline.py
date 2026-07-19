"""
GET /api/pipeline, PATCH /api/pipeline/{target_id}/stage,
GET /api/pipeline/{target_id}/history, GET /api/pipeline/summary.

Business rule 6 (CLAUDE_CRM_MODULE.md section 17): pipeline stage history is
immutable — every stage change is logged with who moved it and when.
PipelineRecord is a current-state snapshot (overwritten in place);
PipelineHistory is the append-only audit row (only ever inserted, never
updated or deleted) — both writes happen in one commit so they can't diverge.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import InvestorTarget, PipelineHistory, PipelineRecord
from app.db.session import get_tenant_db
from app.services.alert_dispatcher import create_alert

router = APIRouter()

_READ_PERMS = ("read:own_raise", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:pipeline", "*")


@router.get("", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_pipeline(db: AsyncSession = Depends(get_tenant_db)):
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


@router.get("/summary", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def pipeline_summary(db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(
        select(PipelineRecord.stage, func.count()).group_by(PipelineRecord.stage)
    )).all()
    return {"by_stage": {stage: count for stage, count in rows}}


class StageMoveRequest(BaseModel):
    stage: str
    reason: str | None = None


@router.patch("/{target_id}/stage", dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def move_stage(
    target_id: uuid.UUID, body: StageMoveRequest, request: Request, db: AsyncSession = Depends(get_tenant_db),
):
    record = (
        await db.execute(select(PipelineRecord).where(PipelineRecord.investor_target_id == target_id))
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="No pipeline record for this investor target.")

    claims = request.state.claims or {}
    moved_by = claims.get("email", "unknown")
    now = datetime.now(timezone.utc)
    old_stage = record.stage

    record.previous_stage = old_stage
    record.stage = body.stage
    record.stage_entered_at = now
    record.stage_updated_by = moved_by
    record.days_in_stage = 0

    db.add(PipelineHistory(
        investor_target_id=target_id,
        from_stage=old_stage,
        to_stage=body.stage,
        moved_by=moved_by,
        moved_at=now,
        reason=body.reason,
    ))

    await db.commit()

    if request.state.client_id:
        target = await db.get(InvestorTarget, target_id)
        await create_alert(
            db, request.state.client_id,
            alert_type="pipeline_movement", severity="info",
            title="Pipeline movement",
            message=f"{target.full_name if target else 'An investor'} moved to {body.stage}",
            related_investor_id=target_id,
        )

    return {"investor_target_id": str(target_id), "from_stage": old_stage, "to_stage": body.stage}


@router.get("/{target_id}/history", dependencies=[Depends(require_permission(*_READ_PERMS))])
async def stage_history(target_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(
        select(PipelineHistory)
        .where(PipelineHistory.investor_target_id == target_id)
        .order_by(PipelineHistory.moved_at)
    )).scalars().all()
    return {
        "history": [
            {
                "from_stage": h.from_stage, "to_stage": h.to_stage,
                "moved_by": h.moved_by, "moved_at": h.moved_at.isoformat() if h.moved_at else None,
                "reason": h.reason,
            }
            for h in rows
        ]
    }
