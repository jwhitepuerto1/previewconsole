"""
Phase 6 production smoke test — same style as verify_phase1-4.py.

Only Mautic has real credentials in this deployment; Smartlead, SuiteCRM,
and North Capital have none, so this checks what's actually verifiable
without them: the best-effort no-op paths never break their host endpoints,
the North Capital webhook's auth/validation/success paths (using a manually
seeded onboarding record so the success path is deterministic rather than
depending on a real North Capital account existing), and the positive_reply
alert wired into the Smartlead webhook.

Run from inside the deployed api container:
    docker compose exec api python scripts/verify_phase6.py
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
from app.db.models.client_raise import Campaign, OnboardingRecord
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

    cc_email = f"verify6-ccadmin-{run_id}@capitalcontext.internal"
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
            "company_name": f"Phase6 Verify {run_id}", "primary_contact_name": "Verify Bot",
            "primary_contact_email": f"verify6-client-{run_id}@capitalcontext.internal",
            "deal_type": "cre_syndication", "raise_target_amount": 1000000,
        })
        check("POST /api/accounts (provisions client DB)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")
        if resp.status_code != 200:
            return
        client_id = resp.json()["id"]

        rep_email = f"verify6-rep-{run_id}@capitalcontext.internal"
        async with Session() as session:
            rep_id = await create_user(session, rep_email, "support_manager", None, password)
            session.add(PlatformSupportAssignment(rep_user_id=rep_id, client_id=uuid.UUID(client_id), is_active=True))
            await session.commit()

        resp = await client.post("/auth/login", json={"email": rep_email, "password": password})
        rep_headers = {"Authorization": f"Bearer {resp.json()['token']}", "X-Acting-Client-Id": client_id}

        resp = await client.post("/api/targets", headers=rep_headers, json={
            "full_name": "Verify Investor 6", "email": "investor6@example.com", "company": "Test Capital",
        })
        target_id = resp.json()["id"] if resp.status_code == 200 else None
        check("create target", resp.status_code == 200, f"HTTP {resp.status_code}")

        # --- SuiteCRM best-effort: pipeline move must succeed even unconfigured ---
        resp = await client.patch(f"/api/pipeline/{target_id}/stage", headers=rep_headers, json={"stage": "qualified"})
        check("pipeline move succeeds with SuiteCRM unconfigured (best-effort no-op)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")

        resp = await client.post("/api/meetings", headers=rep_headers, json={
            "investor_target_id": target_id, "meeting_type": "intro_call", "scheduled_at": "2026-08-01T15:00:00Z",
        })
        meeting_id = resp.json()["id"] if resp.status_code == 200 else None
        resp = await client.patch(f"/api/meetings/{meeting_id}", headers=rep_headers, json={"outcome": "positive"})
        check("meeting outcome update succeeds with SuiteCRM unconfigured (best-effort no-op)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")

        # --- North Capital best-effort: onboarding initiate must succeed even unconfigured ---
        resp = await client.post("/api/onboarding", headers=rep_headers, json={"investor_target_id": target_id, "investment_amount": 100000})
        check(
            "onboarding initiate succeeds with North Capital unconfigured, reference stays null",
            resp.status_code == 200 and resp.json().get("kyc_provider") is None,
            f"HTTP {resp.status_code}: {resp.text[:150]}",
        )

        # --- North Capital webhook: auth + validation + success path ---
        resp = await client.post(
            f"/api/onboarding/webhooks/north-capital/{client_id}",
            json={"event_type": "kyc_complete", "reference": "fake-ref"},
            headers={"X-Webhook-Secret": "wrong-secret"},
        )
        check("North Capital webhook rejects wrong secret", resp.status_code == 401, f"HTTP {resp.status_code}")

        if not settings.north_capital_webhook_secret:
            check("North Capital webhook success path — SKIPPED (NORTH_CAPITAL_WEBHOOK_SECRET not set)", True, "set the env var to exercise this")
        else:
            # A second, separate investor — target_id already has an
            # onboarding record from the initiate call above; reusing it here
            # would create two rows for the same investor and conflate this
            # webhook test with that unrelated scenario.
            resp = await client.post("/api/targets", headers=rep_headers, json={"full_name": "Verify Investor 6b", "email": "investor6b@example.com"})
            target_id_2 = resp.json()["id"]

            # Seed a real onboarding record with a known reference directly in
            # the client DB, so the webhook's success path is deterministic
            # rather than depending on a real North Capital account existing.
            async with Session() as session:
                account = await session.get(PlatformAccount, uuid.UUID(client_id))
            _, client_sessionmaker = get_engine(account.client_db_url)
            async with client_sessionmaker() as client_db:
                record = OnboardingRecord(investor_target_id=uuid.UUID(target_id_2), status="initiated", north_capital_reference="test-ref-123")
                client_db.add(record)
                await client_db.commit()

            resp = await client.post(
                f"/api/onboarding/webhooks/north-capital/{client_id}",
                json={"event_type": "kyc_complete", "reference": "test-ref-123"},
                headers={"X-Webhook-Secret": settings.north_capital_webhook_secret},
            )
            check("North Capital webhook accepts valid secret + known reference", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")

            resp = await client.get(f"/api/onboarding/{target_id_2}", headers=rep_headers)
            check(
                "webhook update reflected — status kyc_complete, kyc_completed_at set",
                resp.status_code == 200 and resp.json().get("status") == "kyc_complete" and resp.json().get("kyc_completed_at") is not None,
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        # --- Smartlead positive_reply alert ---
        if not settings.smartlead_webhook_secret:
            check("Smartlead positive_reply alert — SKIPPED (SMARTLEAD_WEBHOOK_SECRET not set)", True, "set the env var to exercise this")
        else:
            resp = await client.post("/api/campaigns", headers=rep_headers, json={"campaign_name": "Verify Campaign 6", "channel": "email"})
            campaign_id = resp.json()["id"] if resp.status_code == 200 else None
            # smartlead_campaign_id is only set by launch (best-effort, stays
            # null without a real key) — set it directly so the webhook's
            # campaign lookup has something to match against.
            async with Session() as session:
                account = await session.get(PlatformAccount, uuid.UUID(client_id))
            _, client_sessionmaker = get_engine(account.client_db_url)
            async with client_sessionmaker() as client_db:
                campaign = await client_db.get(Campaign, uuid.UUID(campaign_id))
                campaign.smartlead_campaign_id = "sl-test-123"
                await client_db.commit()

            resp = await client.post(
                f"/api/email-events/sync/{client_id}",
                json={
                    "smartlead_campaign_id": "sl-test-123", "lead_email": "investor6@example.com",
                    "event_type": "replied", "subject_line": "Re: Intro",
                },
                headers={"X-Webhook-Secret": settings.smartlead_webhook_secret},
            )
            check("Smartlead webhook accepts replied event", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")

            resp = await client.get("/api/alerts", headers=rep_headers)
            alert_types = {a["alert_type"] for a in resp.json()} if resp.status_code == 200 else set()
            check("positive_reply alert persisted", "positive_reply" in alert_types, f"types={alert_types}")

    await engine.dispose()

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
