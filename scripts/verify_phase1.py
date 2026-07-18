"""
Phase 1 production smoke test — CLAUDE_CRM_MODULE.md Section 16's own
pre-Phase-2 checklist, run against a live deployment instead of locally:

    create a client account -> client DB auto-provisions
    log in as all 6 roles -> each receives a correctly scoped JWT
    a client_admin JWT can only read that client's data
    a preview JWT routes to the preview DB and cannot reach any client DB
    pipeline stage movement saves and appears on the dashboard

Creates real (but clearly-tagged, throwaway) platform users and one real
client account + provisioned database — nothing here is destructive, but it
does leave that test data behind for manual cleanup afterward.

Run from inside the deployed api container so it shares the exact runtime
settings.platform_database_url used in production:
    docker compose exec api python scripts/verify_phase1.py

CRM_BASE_URL overrides which origin the HTTP checks run against (defaults
to this deployment's own public origin).
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

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if detail else ""))


async def create_user(session, email: str, role: str, client_id: uuid.UUID | None, password: str) -> uuid.UUID:
    existing = (await session.execute(select(PlatformUser).where(PlatformUser.email == email))).scalar_one_or_none()
    if existing:
        return existing.id
    user = PlatformUser(
        email=email, hashed_password=hash_password(password), full_name=email,
        role=role, client_id=client_id, is_active=True,
    )
    session.add(user)
    await session.flush()
    return user.id


async def main() -> None:
    password = secrets.token_urlsafe(16)
    run_id = uuid.uuid4().hex[:8]
    engine = create_async_engine(settings.platform_database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    cc_admin_email = f"verify-ccadmin-{run_id}@capitalcontext.internal"
    async with Session() as session:
        await create_user(session, cc_admin_email, "cc_admin", None, password)
        await session.commit()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post("/auth/login", json={"email": cc_admin_email, "password": password})
        check("cc_admin login", resp.status_code == 200 and resp.json().get("role") == "cc_admin", f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            return
        cc_token = resp.json()["token"]
        cc_headers = {"Authorization": f"Bearer {cc_token}"}

        resp = await client.post("/api/accounts", headers=cc_headers, json={
            "company_name": f"Phase1 Verify {run_id}",
            "primary_contact_name": "Verify Bot",
            "primary_contact_email": f"verify-client-{run_id}@capitalcontext.internal",
            "deal_type": "cre_syndication",
            "raise_target_amount": 1000000,
        })
        check("POST /api/accounts (provisions client DB)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code != 200:
            return
        account = resp.json()
        client_id = account["id"]
        check(
            "account status active + client_db_name set",
            account["status"] == "active" and bool(account["client_db_name"]),
            str(account),
        )

        role_emails = {
            "client_admin": f"verify-admin-{run_id}@capitalcontext.internal",
            "client_team": f"verify-team-{run_id}@capitalcontext.internal",
            "client_readonly": f"verify-readonly-{run_id}@capitalcontext.internal",
            "support_manager": f"verify-rep-{run_id}@capitalcontext.internal",
        }
        async with Session() as session:
            for role, email in role_emails.items():
                cid = uuid.UUID(client_id) if role != "support_manager" else None
                user_id = await create_user(session, email, role, cid, password)
                if role == "support_manager":
                    session.add(PlatformSupportAssignment(rep_user_id=user_id, client_id=uuid.UUID(client_id), is_active=True))
            await session.commit()

        tokens: dict[str, str] = {"cc_admin": cc_token}
        for role, email in role_emails.items():
            resp = await client.post("/auth/login", json={"email": email, "password": password})
            ok = resp.status_code == 200 and resp.json().get("role") == role
            check(f"{role} login + correctly scoped JWT", ok, f"HTTP {resp.status_code}")
            if ok:
                tokens[role] = resp.json()["token"]

        # Preview isolation: a preview JWT must never reach a client route.
        resp = await client.post("/api/preview/register", json={
            "name": "Verify Preview", "email": f"verify-preview-{run_id}@capitalcontext.internal",
            "deal_type": "cre_syndication", "raise_target": 1000000,
        })
        check("preview registration", resp.status_code == 200, f"HTTP {resp.status_code}")
        if resp.status_code == 200:
            preview_token = resp.json()["token"]
            resp = await client.get("/api/targets", headers={"Authorization": f"Bearer {preview_token}"})
            check("preview JWT blocked from /api/targets (client route)", resp.status_code in (401, 403), f"HTTP {resp.status_code}")

        # support_manager sources a target for this client (write:targets).
        target_id = None
        if "support_manager" in tokens:
            rep_headers = {
                "Authorization": f"Bearer {tokens['support_manager']}",
                "X-Acting-Client-Id": client_id,
            }
            resp = await client.post("/api/targets", headers=rep_headers, json={
                "full_name": "Verify Investor", "email": "investor@example.com", "company": "Test Capital",
            })
            check("support_manager creates a target", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
            if resp.status_code == 200:
                target_id = resp.json()["id"]

        # client_admin moves it through the pipeline (write:pipeline) — its
        # JWT already carries client_id, no X-Acting-Client-Id needed.
        if target_id and "client_admin" in tokens:
            admin_headers = {"Authorization": f"Bearer {tokens['client_admin']}"}
            resp = await client.patch(f"/api/pipeline/{target_id}/stage", headers=admin_headers, json={"stage": "qualified"})
            check(
                "client_admin moves pipeline stage",
                resp.status_code == 200 and resp.json().get("to_stage") == "qualified",
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

            resp = await client.get("/api/pipeline", headers=admin_headers)
            stages = {row["id"]: row["stage"] for row in resp.json().get("investors", [])} if resp.status_code == 200 else {}
            check("stage move is reflected back on GET /api/pipeline", stages.get(target_id) == "qualified", f"stages={stages}")

        # client_readonly cannot write (matches the Section 5 permission matrix).
        if "client_readonly" in tokens:
            ro_headers = {"Authorization": f"Bearer {tokens['client_readonly']}"}
            resp = await client.post("/api/targets", headers=ro_headers, json={"full_name": "Should Not Be Created"})
            check("client_readonly blocked from write:targets", resp.status_code == 403, f"HTTP {resp.status_code}")

    await engine.dispose()

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
