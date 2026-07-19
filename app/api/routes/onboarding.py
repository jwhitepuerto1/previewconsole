"""
GET/POST /api/onboarding, GET /{target_id} (by investor), PATCH /{id}/status,
GET/PATCH /{id}/checklist(/{item_id}) (by onboarding record id) — section 8's
own route list uses {target_id} for the by-investor lookup and {id} for
every other onboarding_record-scoped route, kept literal here.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import InvestorTarget, OnboardingChecklistItem, OnboardingRecord
from app.db.session import get_tenant_db
from app.services.alert_dispatcher import create_alert

router = APIRouter()

_READ_PERMS = ("read:onboarding", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:onboarding", "*")


class OnboardingOut(BaseModel):
    id: uuid.UUID
    investor_target_id: uuid.UUID | None
    investment_amount: int | None
    structure: str | None
    status: str | None
    kyc_provider: str | None
    kyc_completed_at: datetime | None
    subscription_doc_sent_at: datetime | None
    subscription_doc_signed_at: datetime | None
    accreditation_verified_at: datetime | None


class CreateOnboardingRequest(BaseModel):
    investor_target_id: uuid.UUID
    investment_amount: int | None = None
    structure: str = "equity"


class UpdateStatusRequest(BaseModel):
    status: str


def _to_out(o: OnboardingRecord) -> OnboardingOut:
    return OnboardingOut(
        id=o.id, investor_target_id=o.investor_target_id, investment_amount=o.investment_amount,
        structure=o.structure, status=o.status, kyc_provider=o.kyc_provider,
        kyc_completed_at=o.kyc_completed_at, subscription_doc_sent_at=o.subscription_doc_sent_at,
        subscription_doc_signed_at=o.subscription_doc_signed_at, accreditation_verified_at=o.accreditation_verified_at,
    )


@router.get("", response_model=list[OnboardingOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_onboarding(db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(select(OnboardingRecord))).scalars().all()
    return [_to_out(o) for o in rows]


@router.get("/{target_id}", response_model=OnboardingOut, dependencies=[Depends(require_permission(*_READ_PERMS))])
async def get_onboarding_for_target(target_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    record = (
        await db.execute(select(OnboardingRecord).where(OnboardingRecord.investor_target_id == target_id))
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="No onboarding record for this investor target.")
    return _to_out(record)


@router.post("", response_model=OnboardingOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def initiate_onboarding(body: CreateOnboardingRequest, db: AsyncSession = Depends(get_tenant_db)):
    record = OnboardingRecord(
        investor_target_id=body.investor_target_id, investment_amount=body.investment_amount,
        structure=body.structure, status="initiated",
    )
    db.add(record)
    await db.commit()
    return _to_out(record)


@router.patch("/{onboarding_id}/status", response_model=OnboardingOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_status(onboarding_id: uuid.UUID, body: UpdateStatusRequest, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    record = await db.get(OnboardingRecord, onboarding_id)
    if not record:
        raise HTTPException(status_code=404, detail="Onboarding record not found.")

    now = datetime.now(timezone.utc)
    record.status = body.status
    if body.status == "kyc_complete":
        record.kyc_completed_at = now
    elif body.status == "docs_sent":
        record.subscription_doc_sent_at = now
    elif body.status == "docs_signed":
        record.subscription_doc_signed_at = now
    elif body.status == "accreditation_complete":
        record.accreditation_verified_at = now

    await db.commit()

    if request.state.client_id:
        target = await db.get(InvestorTarget, record.investor_target_id) if record.investor_target_id else None
        await create_alert(
            db, request.state.client_id,
            alert_type="onboarding_update", severity="info",
            title="Onboarding update",
            message=f"{target.full_name if target else 'An investor'} onboarding: {body.status}",
            related_investor_id=record.investor_target_id,
        )

    return _to_out(record)


class ChecklistItemOut(BaseModel):
    id: uuid.UUID
    item_name: str | None
    item_type: str | None
    status: str | None
    due_date: date | None
    completed_at: datetime | None


@router.get("/{onboarding_id}/checklist", response_model=list[ChecklistItemOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_checklist(onboarding_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (
        await db.execute(select(OnboardingChecklistItem).where(OnboardingChecklistItem.onboarding_record_id == onboarding_id))
    ).scalars().all()
    return [
        ChecklistItemOut(id=i.id, item_name=i.item_name, item_type=i.item_type, status=i.status, due_date=i.due_date, completed_at=i.completed_at)
        for i in rows
    ]


class UpdateChecklistItemRequest(BaseModel):
    status: str


@router.patch("/{onboarding_id}/checklist/{item_id}", response_model=ChecklistItemOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_checklist_item(onboarding_id: uuid.UUID, item_id: uuid.UUID, body: UpdateChecklistItemRequest, db: AsyncSession = Depends(get_tenant_db)):
    item = await db.get(OnboardingChecklistItem, item_id)
    if not item or item.onboarding_record_id != onboarding_id:
        raise HTTPException(status_code=404, detail="Checklist item not found.")
    item.status = body.status
    if body.status in ("received", "verified"):
        item.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return ChecklistItemOut(id=item.id, item_name=item.item_name, item_type=item.item_type, status=item.status, due_date=item.due_date, completed_at=item.completed_at)
