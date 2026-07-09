"""
GET/POST /api/targets — investor target management.
Per the spec's own permission matrix, only support_manager/cc_admin have
write:targets — client roles can read but not add targets, matching the
spec's narrative that targets are "sourced from Universe DB by CC rep."
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import InvestorTarget, PipelineRecord
from app.db.session import get_tenant_db

router = APIRouter()


class TargetOut(BaseModel):
    id: uuid.UUID
    full_name: str | None
    email: str | None
    company: str | None
    title: str | None
    investor_type: str | None
    fit_score: int | None
    status: str | None


class CreateTargetRequest(BaseModel):
    full_name: str
    email: str | None = None
    linkedin_url: str | None = None
    title: str | None = None
    company: str | None = None
    investor_type: str | None = None
    geography: str | None = None
    fit_score: int | None = None
    added_by: str = "rep"


@router.get("", response_model=list[TargetOut], dependencies=[Depends(require_permission(
    "read:own_raise", "read:all_assigned_clients", "*",
))])
async def list_targets(db: AsyncSession = Depends(get_tenant_db)):
    targets = (await db.execute(select(InvestorTarget))).scalars().all()
    return [
        TargetOut(
            id=t.id, full_name=t.full_name, email=t.email, company=t.company,
            title=t.title, investor_type=t.investor_type, fit_score=t.fit_score, status=t.status,
        )
        for t in targets
    ]


@router.post("", response_model=TargetOut, dependencies=[Depends(require_permission("write:targets", "*"))])
async def create_target(body: CreateTargetRequest, db: AsyncSession = Depends(get_tenant_db)):
    target = InvestorTarget(
        full_name=body.full_name,
        email=body.email,
        linkedin_url=body.linkedin_url,
        title=body.title,
        company=body.company,
        investor_type=body.investor_type,
        geography=body.geography,
        fit_score=body.fit_score,
        status="active",
        added_by=body.added_by,
    )
    db.add(target)
    await db.flush()  # assigns target.id

    # Paired PipelineRecord — required because /api/pipeline (and preview's
    # equivalent) inner-joins on it; a target without one would silently
    # vanish from the pipeline view rather than error.
    db.add(PipelineRecord(investor_target_id=target.id, stage="prospect"))

    await db.commit()
    return TargetOut(
        id=target.id, full_name=target.full_name, email=target.email, company=target.company,
        title=target.title, investor_type=target.investor_type, fit_score=target.fit_score, status=target.status,
    )
