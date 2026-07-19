"""
Phase 3 production smoke test — data room (with the client_readonly gated
view), onboarding + checklist, and funding events (with real-time summary
maintenance), the same style as verify_phase1.py/verify_phase2.py.

Run from inside the deployed api container:
    docker compose exec api python scripts/verify_phase3.py
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
from app.db.models.client_raise import OnboardingChecklistItem
from app.db.models.platform import PlatformAccount, PlatformSupportAssignment, PlatformUser
from app.db.session import get_engine

BASE_URL = os.environ.get("CRM_BASE_URL", "https://customdocker-u58165.vm.elestio.app")

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if detail else ""))


async def create_user(session, email: str, role: str, client_id: uuid.UUID | None, password: str) -> uuid.UUID:
    existing = (await session.execute(select(PlatformUser).where(PlatformUser.email == email))).scalar_one_or_none()
    if existing:
        return existing.id
    user = PlatformUser(email=email, hashed_password=hash_password(password), full_name=email, role=role, client_id=client_id, is_active=True)
    session.add(user)
    await session.flush()
    return user.id


async def main() -> None:
    password = secrets.token_urlsafe(16)
    run_id = uuid.uuid4().hex[:8]
    engine = create_async_engine(settings.platform_database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    cc_email = f"verify3-ccadmin-{run_id}@capitalcontext.internal"
    async with Session() as session:
        await create_user(session, cc_email, "cc_admin", None, password)
        await session.commit()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post("/auth/login", json={"email": cc_email, "password": password})
        check("cc_admin login", resp.status_code == 200, f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            return
        cc_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = await client.post("/api/accounts", headers=cc_headers, json={
            "company_name": f"Phase3 Verify {run_id}", "primary_contact_name": "Verify Bot",
            "primary_contact_email": f"verify3-client-{run_id}@capitalcontext.internal",
            "deal_type": "cre_syndication", "raise_target_amount": 1000000,
        })
        check("POST /api/accounts (provisions client DB)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code != 200:
            return
        client_id = resp.json()["id"]

        admin_email = f"verify3-admin-{run_id}@capitalcontext.internal"
        team_email = f"verify3-team-{run_id}@capitalcontext.internal"
        ro_email = f"verify3-readonly-{run_id}@capitalcontext.internal"
        rep_email = f"verify3-rep-{run_id}@capitalcontext.internal"
        async with Session() as session:
            await create_user(session, admin_email, "client_admin", uuid.UUID(client_id), password)
            await create_user(session, team_email, "client_team", uuid.UUID(client_id), password)
            await create_user(session, ro_email, "client_readonly", uuid.UUID(client_id), password)
            rep_id = await create_user(session, rep_email, "support_manager", None, password)
            session.add(PlatformSupportAssignment(rep_user_id=rep_id, client_id=uuid.UUID(client_id), is_active=True))
            await session.commit()

        headers = {}
        for role_key, email, role_name in [
            ("admin", admin_email, "client_admin"), ("team", team_email, "client_team"),
            ("readonly", ro_email, "client_readonly"), ("rep", rep_email, "support_manager"),
        ]:
            resp = await client.post("/auth/login", json={"email": email, "password": password})
            ok = resp.status_code == 200
            if ok:
                h = {"Authorization": f"Bearer {resp.json()['token']}"}
                if role_name == "support_manager":
                    h["X-Acting-Client-Id"] = client_id
                headers[role_key] = h
        check("all 4 role logins", len(headers) == 4, f"got={list(headers)}")
        if len(headers) != 4:
            return

        # --- a target to hang onboarding/funding off of ---
        resp = await client.post("/api/targets", headers=headers["rep"], json={
            "full_name": "Verify Investor 3", "email": "investor3@example.com", "company": "Test Capital",
        })
        check("support_manager creates a target", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        target_id = resp.json()["id"] if resp.status_code == 200 else None

        # --- data room: upload one public + one qualified doc ---
        resp = await client.post("/api/data-room", headers=headers["admin"], json={
            "document_name": "Exec Summary", "document_type": "exec_summary",
            "file_path": "/docs/exec.pdf", "access_level": "public",
        })
        check("client_admin uploads public document", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        public_doc_id = resp.json()["id"] if resp.status_code == 200 else None

        resp = await client.post("/api/data-room", headers=headers["admin"], json={
            "document_name": "Financial Model", "document_type": "financial_model",
            "file_path": "/docs/model.xlsx", "access_level": "qualified",
        })
        check("client_admin uploads qualified document", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        qualified_doc_id = resp.json()["id"] if resp.status_code == 200 else None

        resp = await client.post("/api/data-room", headers=headers["team"], json={
            "document_name": "Should Fail", "document_type": "other", "file_path": "/x", "access_level": "public",
        })
        check("client_team blocked from write:data_room", resp.status_code == 403, f"HTTP {resp.status_code}")

        resp = await client.get("/api/data-room", headers=headers["admin"])
        check(
            "client_admin sees both documents (full read)",
            resp.status_code == 200 and len(resp.json()) == 2,
            f"HTTP {resp.status_code}: {resp.text[:200]}",
        )

        resp = await client.get("/api/data-room", headers=headers["readonly"])
        docs = resp.json() if resp.status_code == 200 else []
        check(
            "client_readonly sees only the public document (gated read)",
            resp.status_code == 200 and len(docs) == 1 and docs[0]["access_level"] == "public",
            f"HTTP {resp.status_code}: {docs}",
        )

        if qualified_doc_id and target_id:
            resp = await client.post(f"/api/data-room/{qualified_doc_id}/grant-access/{target_id}", headers=headers["rep"])
            check("grant-access on a document", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
            resp = await client.get(f"/api/data-room/{qualified_doc_id}/access-log", headers=headers["admin"])
            check(
                "grant recorded in access log",
                resp.status_code == 200 and len(resp.json()["access_log"]) == 1,
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        # --- onboarding ---
        if target_id:
            resp = await client.post("/api/onboarding", headers=headers["admin"], json={"investor_target_id": target_id})
            check("client_admin blocked from write:onboarding", resp.status_code == 403, f"HTTP {resp.status_code}")

            resp = await client.post("/api/onboarding", headers=headers["rep"], json={
                "investor_target_id": target_id, "investment_amount": 250000, "structure": "equity",
            })
            check("support_manager initiates onboarding", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
            onboarding_id = resp.json()["id"] if resp.status_code == 200 else None

            if onboarding_id:
                resp = await client.get(f"/api/onboarding/{target_id}", headers=headers["admin"])
                check("client_admin reads onboarding by target id", resp.status_code == 200, f"HTTP {resp.status_code}")

                resp = await client.patch(f"/api/onboarding/{onboarding_id}/status", headers=headers["rep"], json={"status": "kyc_complete"})
                check(
                    "update onboarding status sets kyc_completed_at",
                    resp.status_code == 200 and resp.json()["kyc_completed_at"] is not None,
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

                # No POST for checklist items in the spec's own route list —
                # seed one directly in the client's provisioned DB, matching
                # how a real onboarding workflow would pre-populate a checklist.
                async with Session() as session:
                    account = (await session.execute(select(PlatformAccount).where(PlatformAccount.id == uuid.UUID(client_id)))).scalar_one()
                _, client_sessionmaker = get_engine(account.client_db_url)
                async with client_sessionmaker() as client_db:
                    item = OnboardingChecklistItem(onboarding_record_id=uuid.UUID(onboarding_id), item_name="Subscription doc", item_type="subscription_doc", status="pending")
                    client_db.add(item)
                    await client_db.commit()
                    await client_db.refresh(item)
                    item_id = str(item.id)

                resp = await client.get(f"/api/onboarding/{onboarding_id}/checklist", headers=headers["admin"])
                check("list checklist items", resp.status_code == 200 and len(resp.json()) == 1, f"HTTP {resp.status_code}")

                resp = await client.patch(f"/api/onboarding/{onboarding_id}/checklist/{item_id}", headers=headers["rep"], json={"status": "verified"})
                check(
                    "mark checklist item verified sets completed_at",
                    resp.status_code == 200 and resp.json()["completed_at"] is not None,
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

        # --- funding: real-time summary maintenance ---
        resp = await client.get("/api/funding/summary", headers=headers["admin"])
        before = resp.json() if resp.status_code == 200 else {}
        check("get funding summary (auto-created if missing)", resp.status_code == 200, f"HTTP {resp.status_code}: {before}")

        resp = await client.post("/api/funding/events", headers=headers["admin"], json={
            "investor_target_id": target_id, "event_type": "soft_commit", "amount": 250000,
        })
        check("client_admin blocked from write:funding", resp.status_code == 403, f"HTTP {resp.status_code}")

        resp = await client.post("/api/funding/events", headers=headers["rep"], json={
            "investor_target_id": target_id, "event_type": "soft_commit", "amount": 250000,
        })
        check("support_manager logs a soft_commit funding event", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")

        resp = await client.get("/api/funding/summary", headers=headers["admin"])
        after = resp.json() if resp.status_code == 200 else {}
        check(
            "funding summary updated in real time (no manual reconciliation)",
            resp.status_code == 200 and after.get("soft_committed") == before.get("soft_committed", 0) + 250000,
            f"before={before} after={after}",
        )

        resp = await client.get("/api/alerts", headers=headers["rep"])
        alert_types = {a["alert_type"] for a in resp.json()} if resp.status_code == 200 else set()
        check(
            "onboarding_update and funding_event alerts both persisted",
            {"onboarding_update", "funding_event"}.issubset(alert_types),
            f"HTTP {resp.status_code}: types={alert_types}",
        )

    await engine.dispose()

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
