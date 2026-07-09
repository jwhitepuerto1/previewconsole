"""
POST /auth/login — role-agnostic. Looks up the PlatformUser by email,
verifies the password, and issues the token shape appropriate to that
user's stored role.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_client_token, create_support_token, verify_password
from app.db.models.platform import PlatformAccount, PlatformSupportAssignment, PlatformUser
from app.db.session import get_platform_db

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    email: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_platform_db)):
    user = (
        await db.execute(select(PlatformUser).where(PlatformUser.email == body.email))
    ).scalar_one_or_none()

    if not user or not user.is_active or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if user.role in ("client_admin", "client_team", "client_readonly"):
        if not user.client_id:
            raise HTTPException(status_code=500, detail="Client user has no associated client_id.")
        account = (
            await db.execute(select(PlatformAccount).where(PlatformAccount.id == user.client_id))
        ).scalar_one_or_none()
        if not account or not account.client_db_name:
            raise HTTPException(status_code=403, detail="Client account not found or not provisioned.")
        token = create_client_token(user.id, user.email, user.role, user.client_id, account.client_db_name)

    elif user.role in ("support_manager", "cc_admin"):
        assigned_clients: list[str] = []
        if user.role == "support_manager":
            rows = (
                await db.execute(
                    select(PlatformSupportAssignment.client_id).where(
                        PlatformSupportAssignment.rep_user_id == user.id,
                        PlatformSupportAssignment.is_active == True,  # noqa: E712
                    )
                )
            ).scalars().all()
            assigned_clients = [str(c) for c in rows]
        token = create_support_token(user.id, user.email, user.role, assigned_clients)

    else:
        raise HTTPException(status_code=500, detail=f"Unknown role: {user.role}")

    return LoginResponse(token=token, role=user.role, email=user.email)
