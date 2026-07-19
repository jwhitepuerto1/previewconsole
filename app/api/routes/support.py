"""
GET /api/support/overview, /clients, /alerts — cross-client view for reps
(section 15 Phase 4). POST .../escalate and .../resolve-escalation aren't
in section 8's literal route list (written before Phase 4 existed), but
Phase 4's own build list explicitly calls for "escalation flag system — rep
can flag a raise for senior review", so some endpoint has to exist; these
follow the same require_permission("read:support_dashboard", "*") gate as
everything else here since the matrix has no dedicated write permission for
this role's own dashboard actions.

Escalation state isn't a new column (section 6/7 have no field for it) — it's
derived from the latest platform_audit_log row tagged escalation_flagged/
escalation_resolved for that client, the same audit-trail pattern
accounts.py already uses for account_created/provisioning_failed.

Every route here fans out across each assigned client's own database
(section 2's one-DB-per-client architecture) concurrently via asyncio.gather
— there is no single query that spans clients by design.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import (
    Campaign, FundingSummary, InvestorTarget, PipelineHistory, RaiseAlert, RaiseConfig,
)
from app.db.models.platform import PlatformAccount, PlatformAuditLog
from app.db.session import get_engine, get_platform_db

router = APIRouter()

_PERMS = ("read:support_dashboard", "*")


async def _assigned_accounts(request: Request, platform_db: AsyncSession) -> list[PlatformAccount]:
    claims = request.state.claims or {}
    query = select(PlatformAccount).where(PlatformAccount.client_db_url.is_not(None))
    if claims.get("role") != "cc_admin":
        assigned = [uuid.UUID(c) for c in (claims.get("assigned_clients") or [])]
        if not assigned:
            return []
        query = query.where(PlatformAccount.id.in_(assigned))
    return (await platform_db.execute(query)).scalars().all()


async def _escalation_status(platform_db: AsyncSession, client_id: uuid.UUID) -> bool:
    row = (
        await platform_db.execute(
            select(PlatformAuditLog.action)
            .where(PlatformAuditLog.client_id == client_id, PlatformAuditLog.action.in_(["escalation_flagged", "escalation_resolved"]))
            .order_by(PlatformAuditLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row == "escalation_flagged"


async def _client_health(account: PlatformAccount) -> dict:
    _, sessionmaker = get_engine(account.client_db_url)
    async with sessionmaker() as db:
        config = (await db.execute(select(RaiseConfig))).scalars().first()
        investor_count = (await db.execute(select(func.count()).select_from(InvestorTarget))).scalar_one()
        funding = (await db.execute(select(FundingSummary))).scalars().first()
        last_move = (await db.execute(select(func.max(PipelineHistory.moved_at)))).scalar_one()
        active_campaigns = (
            await db.execute(select(func.count()).select_from(Campaign).where(Campaign.status == "active"))
        ).scalar_one()

    days_since_movement = None
    if last_move:
        moved_at = last_move if last_move.tzinfo else last_move.replace(tzinfo=timezone.utc)
        days_since_movement = (datetime.now(timezone.utc) - moved_at).days

    return {
        "client_id": str(account.id),
        "company_name": account.company_name,
        "status": account.status,
        "raise_name": config.raise_name if config else None,
        "raise_status": config.status if config else None,
        "investor_count": investor_count,
        "percent_raised": funding.percent_raised if funding else 0.0,
        "days_since_last_movement": days_since_movement,
        "active_campaign_count": active_campaigns,
        "needs_attention": days_since_movement is None or days_since_movement > 7,
    }


@router.get("/clients", dependencies=[Depends(require_permission(*_PERMS))])
async def support_clients(request: Request, platform_db: AsyncSession = Depends(get_platform_db)):
    accounts = await _assigned_accounts(request, platform_db)
    rows = await asyncio.gather(*(_client_health(a) for a in accounts))
    for row, account in zip(rows, accounts):
        row["is_escalated"] = await _escalation_status(platform_db, account.id)
    return {"clients": rows}


@router.get("/overview", dependencies=[Depends(require_permission(*_PERMS))])
async def support_overview(request: Request, platform_db: AsyncSession = Depends(get_platform_db)):
    accounts = await _assigned_accounts(request, platform_db)
    rows = await asyncio.gather(*(_client_health(a) for a in accounts))
    for row, account in zip(rows, accounts):
        row["is_escalated"] = await _escalation_status(platform_db, account.id)

    return {
        "total_clients": len(rows),
        "needs_attention_count": sum(1 for r in rows if r["needs_attention"]),
        "escalated_count": sum(1 for r in rows if r["is_escalated"]),
        "average_percent_raised": round(sum(r["percent_raised"] for r in rows) / len(rows), 4) if rows else 0.0,
        "clients": rows,
    }


@router.get("/alerts", dependencies=[Depends(require_permission(*_PERMS))])
async def support_alerts(request: Request, platform_db: AsyncSession = Depends(get_platform_db)):
    accounts = await _assigned_accounts(request, platform_db)

    async def _client_alerts(account: PlatformAccount) -> list[dict]:
        _, sessionmaker = get_engine(account.client_db_url)
        async with sessionmaker() as db:
            rows = (await db.execute(select(RaiseAlert).order_by(RaiseAlert.created_at.desc()).limit(50))).scalars().all()
        return [
            {
                "client_id": str(account.id), "company_name": account.company_name,
                "id": str(a.id), "alert_type": a.alert_type, "severity": a.severity,
                "title": a.title, "message": a.message, "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
            }
            for a in rows
        ]

    per_client = await asyncio.gather(*(_client_alerts(a) for a in accounts))
    alerts = [a for client_alerts in per_client for a in client_alerts]
    alerts.sort(key=lambda a: a["created_at"], reverse=True)
    return {"alerts": alerts}


class EscalateRequest(BaseModel):
    reason: str


@router.post("/clients/{client_id}/escalate", dependencies=[Depends(require_permission(*_PERMS))])
async def escalate_client(client_id: uuid.UUID, body: EscalateRequest, request: Request, platform_db: AsyncSession = Depends(get_platform_db)):
    account = await platform_db.get(PlatformAccount, client_id)
    if not account:
        raise HTTPException(status_code=404, detail="Client account not found.")
    claims = request.state.claims or {}
    platform_db.add(PlatformAuditLog(
        user_id=uuid.UUID(claims["sub"]) if claims.get("sub") else None,
        user_role=claims.get("role"), client_id=client_id,
        action="escalation_flagged", entity_type="platform_account", entity_id=client_id,
        payload={"reason": body.reason},
    ))
    await platform_db.commit()
    return {"status": "escalated"}


@router.post("/clients/{client_id}/resolve-escalation", dependencies=[Depends(require_permission(*_PERMS))])
async def resolve_escalation(client_id: uuid.UUID, request: Request, platform_db: AsyncSession = Depends(get_platform_db)):
    account = await platform_db.get(PlatformAccount, client_id)
    if not account:
        raise HTTPException(status_code=404, detail="Client account not found.")
    claims = request.state.claims or {}
    platform_db.add(PlatformAuditLog(
        user_id=uuid.UUID(claims["sub"]) if claims.get("sub") else None,
        user_role=claims.get("role"), client_id=client_id,
        action="escalation_resolved", entity_type="platform_account", entity_id=client_id,
        payload={},
    ))
    await platform_db.commit()
    return {"status": "resolved"}
