"""
Account creation and provisioning — cc_admin only.
POST /api/accounts creates the PlatformAccount row, provisions a real
dedicated client database, and seeds an initial raise_config row so the
new client's dashboard is never truly empty.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import RaiseConfig
from app.db.models.platform import PlatformAccount, PlatformAuditLog
from app.db.provisioner import ProvisioningError, provision_client_database
from app.db.session import get_engine, get_platform_db

router = APIRouter()


class CreateAccountRequest(BaseModel):
    company_name: str
    primary_contact_name: str
    primary_contact_email: str
    deal_type: str
    raise_target_amount: int


class AccountResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    status: str
    client_db_name: str | None
    deal_type: str
    raise_target_amount: int


@router.post("", response_model=AccountResponse, dependencies=[Depends(require_permission("write:accounts", "*"))])
async def create_account(body: CreateAccountRequest, db: AsyncSession = Depends(get_platform_db)):
    account = PlatformAccount(
        company_name=body.company_name,
        primary_contact_name=body.primary_contact_name,
        primary_contact_email=body.primary_contact_email,
        deal_type=body.deal_type,
        raise_target_amount=body.raise_target_amount,
        status="provisioning",
    )
    db.add(account)
    await db.flush()  # assigns account.id without committing yet
    account_id = account.id
    await db.commit()

    try:
        db_name, db_url = await provision_client_database(account_id)
    except ProvisioningError as exc:
        account.status = "provisioning_failed"
        db.add(PlatformAuditLog(
            user_id=None,
            user_role="cc_admin",
            client_id=account_id,
            action="provisioning_failed",
            entity_type="platform_account",
            entity_id=account_id,
            payload={"error": str(exc)},
        ))
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {exc}") from exc

    account.client_db_name = db_name
    account.client_db_url = db_url
    account.status = "active"
    account.activated_at = datetime.now(timezone.utc)
    db.add(PlatformAuditLog(
        user_id=None,
        user_role="cc_admin",
        client_id=account_id,
        action="account_created",
        entity_type="platform_account",
        entity_id=account_id,
        payload={"company_name": body.company_name, "deal_type": body.deal_type},
    ))
    await db.commit()

    # Seed the initial raise_config row in the newly provisioned client DB.
    _, client_sessionmaker = get_engine(db_url)
    async with client_sessionmaker() as client_db:
        client_db.add(RaiseConfig(
            client_id=account_id,
            raise_name=body.company_name,
            deal_type=body.deal_type,
            raise_target=body.raise_target_amount,
            status="pre_launch",
        ))
        await client_db.commit()

    return AccountResponse(
        id=account_id, company_name=body.company_name, status="active",
        client_db_name=db_name, deal_type=body.deal_type, raise_target_amount=body.raise_target_amount,
    )


@router.get("", response_model=list[AccountResponse], dependencies=[Depends(require_permission("read:accounts", "*"))])
async def list_accounts(db: AsyncSession = Depends(get_platform_db)):
    accounts = (await db.execute(select(PlatformAccount))).scalars().all()
    return [
        AccountResponse(
            id=a.id, company_name=a.company_name or "", status=a.status or "",
            client_db_name=a.client_db_name, deal_type=a.deal_type or "",
            raise_target_amount=a.raise_target_amount or 0,
        )
        for a in accounts
    ]


@router.get("/{account_id}", response_model=AccountResponse, dependencies=[Depends(require_permission("read:accounts", "*"))])
async def get_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_platform_db)):
    account = (await db.execute(select(PlatformAccount).where(PlatformAccount.id == account_id))).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    return AccountResponse(
        id=account.id, company_name=account.company_name or "", status=account.status or "",
        client_db_name=account.client_db_name, deal_type=account.deal_type or "",
        raise_target_amount=account.raise_target_amount or 0,
    )
