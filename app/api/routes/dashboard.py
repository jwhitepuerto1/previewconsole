"""
GET /api/dashboard — the real (non-preview) raise dashboard. Same shape and
query style as api/routes/preview.py's dashboard route, just against
get_tenant_db (resolved by middleware/auth.py from a real client/support
token) instead of a preview-only dependency.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import FundingSummary, InvestorTarget, PipelineRecord, RaiseConfig
from app.db.session import get_tenant_db

router = APIRouter()


@router.get("", dependencies=[Depends(require_permission("read:own_raise", "read:all_assigned_clients", "*"))])
async def dashboard(db: AsyncSession = Depends(get_tenant_db)):
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
