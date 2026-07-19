"""
One-off: creates a real, persistent client account + login credentials for
manually exploring the finished product in a browser — unlike
verify_phase*.py's accounts, this one is NOT meant to be cleaned up
afterward by cleanup_test_accounts.py (deliberately doesn't match its
"Phase* Verify%"/"verify%@%" naming patterns).

Creates:
  - one cc_admin bootstrap user (only used to call POST /api/accounts once)
  - one real client account + provisioned database
  - one client_admin login (full access to that raise)
  - one support_manager login (rep view — cross-client dashboard, assigned
    to this account)

Passwords are generated and printed once — write them down, they aren't
stored anywhere else in plaintext.

Usage:
    docker compose exec api python scripts/create_demo_account.py
"""
from __future__ import annotations

import asyncio
import os
import secrets
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.platform import PlatformSupportAssignment, PlatformUser

BASE_URL = os.environ.get("CRM_BASE_URL", "https://customdocker-u58165.vm.elestio.app")


async def create_user(session, email: str, role: str, client_id: uuid.UUID | None, password: str) -> uuid.UUID:
    existing = (await session.execute(select(PlatformUser).where(PlatformUser.email == email))).scalar_one_or_none()
    if existing:
        return existing.id
    user = PlatformUser(email=email, hashed_password=hash_password(password), full_name=email, role=role, client_id=client_id, is_active=True)
    session.add(user)
    await session.flush()
    return user.id


async def main() -> None:
    engine = create_async_engine(settings.platform_database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    bootstrap_password = secrets.token_urlsafe(16)
    admin_password = secrets.token_urlsafe(12)
    rep_password = secrets.token_urlsafe(12)

    cc_email = "demo-bootstrap@capitalcontext.internal"
    async with Session() as session:
        await create_user(session, cc_email, "cc_admin", None, bootstrap_password)
        await session.commit()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post("/auth/login", json={"email": cc_email, "password": bootstrap_password})
        resp.raise_for_status()
        cc_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = await client.post("/api/accounts", headers=cc_headers, json={
            "company_name": "Meridian Capital Partners — Live Demo",
            "primary_contact_name": "Demo User",
            "primary_contact_email": "demo-client@capitalcontext.internal",
            "deal_type": "cre_syndication",
            "raise_target_amount": 18_000_000,
        })
        resp.raise_for_status()
        account = resp.json()

    admin_email = "demo-admin@capitalcontext.internal"
    rep_email = "demo-rep@capitalcontext.internal"
    async with Session() as session:
        await create_user(session, admin_email, "client_admin", uuid.UUID(account["id"]), admin_password)
        rep_id = await create_user(session, rep_email, "support_manager", None, rep_password)
        session.add(PlatformSupportAssignment(rep_user_id=rep_id, client_id=uuid.UUID(account["id"]), is_active=True))
        await session.commit()

    await engine.dispose()

    print("Demo account created — this one is permanent, not cleaned up automatically.\n")
    print(f"URL: {BASE_URL}/login\n")
    print(f"Client admin (full access to the raise):\n  email: {admin_email}\n  password: {admin_password}\n")
    print(f"Support manager (rep cross-client view):\n  email: {rep_email}\n  password: {rep_password}\n")
    print("(The cc_admin bootstrap login is internal-only — not meant for browsing the UI.)")


if __name__ == "__main__":
    asyncio.run(main())
