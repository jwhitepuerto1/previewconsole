"""
Phase 2 production smoke test — exercises every route added in the campaign
workflow build (campaigns, LinkedIn, meetings, notes, weekly reports, SSE
alerts) against a live deployment, the same style as verify_phase1.py.

Self-contained: provisions its own throwaway client account rather than
reusing verify_phase1.py's, since that run's user passwords were random and
never persisted anywhere this script could read them back.

Run from inside the deployed api container:
    docker compose exec api python scripts/verify_phase2.py

CRM_BASE_URL overrides the origin the HTTP checks run against.
"""
from __future__ import annotations

import asyncio
import json
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

    cc_admin_email = f"verify2-ccadmin-{run_id}@capitalcontext.internal"
    async with Session() as session:
        await create_user(session, cc_admin_email, "cc_admin", None, password)
        await session.commit()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post("/auth/login", json={"email": cc_admin_email, "password": password})
        check("cc_admin login", resp.status_code == 200, f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            return
        cc_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        resp = await client.post("/api/accounts", headers=cc_headers, json={
            "company_name": f"Phase2 Verify {run_id}",
            "primary_contact_name": "Verify Bot",
            "primary_contact_email": f"verify2-client-{run_id}@capitalcontext.internal",
            "deal_type": "cre_syndication",
            "raise_target_amount": 1000000,
        })
        check("POST /api/accounts (provisions client DB)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code != 200:
            return
        client_id = resp.json()["id"]

        admin_email = f"verify2-admin-{run_id}@capitalcontext.internal"
        rep_email = f"verify2-rep-{run_id}@capitalcontext.internal"
        async with Session() as session:
            admin_id = await create_user(session, admin_email, "client_admin", uuid.UUID(client_id), password)
            rep_id = await create_user(session, rep_email, "support_manager", None, password)
            session.add(PlatformSupportAssignment(rep_user_id=rep_id, client_id=uuid.UUID(client_id), is_active=True))
            await session.commit()

        resp = await client.post("/auth/login", json={"email": admin_email, "password": password})
        admin_headers = {"Authorization": f"Bearer {resp.json()['token']}"} if resp.status_code == 200 else None
        resp = await client.post("/auth/login", json={"email": rep_email, "password": password})
        rep_headers = (
            {"Authorization": f"Bearer {resp.json()['token']}", "X-Acting-Client-Id": client_id}
            if resp.status_code == 200 else None
        )
        check("client_admin + support_manager logins", bool(admin_headers and rep_headers), "")
        if not (admin_headers and rep_headers):
            return

        # --- campaigns: support_manager can, client_admin cannot ---
        resp = await client.post("/api/campaigns", headers=rep_headers, json={"campaign_name": "Verify Campaign", "channel": "email"})
        check("support_manager creates a campaign", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        campaign_id = resp.json()["id"] if resp.status_code == 200 else None

        resp = await client.post("/api/campaigns", headers=admin_headers, json={"campaign_name": "Should Fail", "channel": "email"})
        check("client_admin blocked from write:campaigns", resp.status_code == 403, f"HTTP {resp.status_code}")

        if campaign_id:
            resp = await client.post(f"/api/campaigns/{campaign_id}/launch", headers=rep_headers)
            check(
                "launch campaign (no-op Smartlead, still marks active)",
                resp.status_code == 200 and resp.json().get("status") == "active",
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
            resp = await client.get(f"/api/campaigns/{campaign_id}/metrics", headers=rep_headers)
            check("GET campaign metrics", resp.status_code == 200, f"HTTP {resp.status_code}")
            resp = await client.get(f"/api/campaigns/{campaign_id}/activity", headers=rep_headers)
            check("GET campaign activity", resp.status_code == 200, f"HTTP {resp.status_code}")

        # --- a target to hang meetings/notes/linkedin/pipeline off of ---
        resp = await client.post("/api/targets", headers=rep_headers, json={
            "full_name": "Verify Investor 2", "email": "investor2@example.com", "company": "Test Capital",
        })
        check("support_manager creates a target", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        target_id = resp.json()["id"] if resp.status_code == 200 else None

        if target_id:
            # --- meetings + action items ---
            resp = await client.post("/api/meetings", headers=admin_headers, json={
                "investor_target_id": target_id, "meeting_type": "intro_call",
                "scheduled_at": "2026-08-01T15:00:00Z",
            })
            check("client_admin creates a meeting", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
            meeting_id = resp.json()["id"] if resp.status_code == 200 else None

            if meeting_id:
                resp = await client.post(f"/api/meetings/{meeting_id}/action-items", headers=admin_headers, json={"action": "Send deck"})
                check("create meeting action item", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
                resp = await client.get(f"/api/meetings/{meeting_id}/action-items", headers=admin_headers)
                check(
                    "list meeting action items",
                    resp.status_code == 200 and len(resp.json()) == 1,
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                )

            # --- LinkedIn touchpoint ---
            resp = await client.post("/api/linkedin", headers=admin_headers, json={
                "investor_target_id": target_id, "touchpoint_type": "connection_request",
            })
            check("create LinkedIn touchpoint", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
            resp = await client.get(f"/api/linkedin/{target_id}", headers=admin_headers)
            check(
                "list LinkedIn touchpoints",
                resp.status_code == 200 and len(resp.json()) == 1,
                f"HTTP {resp.status_code}",
            )

            # --- investor note: create, update, delete ---
            resp = await client.post("/api/notes", headers=admin_headers, json={
                "investor_target_id": target_id, "note": "First impression: promising.",
            })
            check("create investor note", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
            note_id = resp.json()["id"] if resp.status_code == 200 else None
            if note_id:
                resp = await client.patch(f"/api/notes/{note_id}", headers=admin_headers, json={"note": "Updated note."})
                check("update investor note", resp.status_code == 200 and resp.json()["note"] == "Updated note.", f"HTTP {resp.status_code}")
                resp = await client.delete(f"/api/notes/{note_id}", headers=admin_headers)
                check("delete investor note", resp.status_code == 204, f"HTTP {resp.status_code}")

            # --- SSE alert: subscribe, move pipeline stage, confirm it arrives live ---
            async def listen_for_alert() -> dict | None:
                async with httpx.AsyncClient(base_url=BASE_URL, timeout=20) as sse_client:
                    async with sse_client.stream("GET", "/api/alerts/stream", headers=admin_headers) as stream:
                        async for line in stream.aiter_lines():
                            if line.startswith("data: "):
                                return json.loads(line[len("data: "):])
                return None

            listener = asyncio.create_task(listen_for_alert())
            await asyncio.sleep(1)  # let the SSE connection establish before triggering the move
            resp = await client.patch(f"/api/pipeline/{target_id}/stage", headers=admin_headers, json={"stage": "qualified"})
            check("client_admin moves pipeline stage", resp.status_code == 200, f"HTTP {resp.status_code}")

            try:
                alert = await asyncio.wait_for(listener, timeout=10)
            except asyncio.TimeoutError:
                alert = None
            check(
                "pipeline_movement alert delivered live over SSE",
                bool(alert and alert.get("alert_type") == "pipeline_movement"),
                f"alert={alert}",
            )

            resp = await client.get("/api/alerts", headers=rep_headers)
            check(
                "alert also persisted to history",
                resp.status_code == 200 and any(a["alert_type"] == "pipeline_movement" for a in resp.json()),
                f"HTTP {resp.status_code}",
            )
            if resp.status_code == 200:
                alert_id = next(a["id"] for a in resp.json() if a["alert_type"] == "pipeline_movement")
                resp = await client.patch(f"/api/alerts/{alert_id}/read", headers=rep_headers)
                check("mark alert read", resp.status_code == 200 and resp.json()["is_read"] is True, f"HTTP {resp.status_code}")

        # --- weekly report: generate, edit commentary, publish, confirm locked ---
        resp = await client.post("/api/reports/generate", headers=rep_headers, json={})
        check("support_manager generates weekly report", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}")
        report_id = resp.json()["id"] if resp.status_code == 200 else None

        if report_id:
            report = resp.json()
            check(
                "report has all four summary blocks",
                all(report.get(k) is not None for k in ("pipeline_summary", "campaign_summary", "meeting_summary", "funding_summary")),
                f"report={report}",
            )
            resp = await client.patch(f"/api/reports/{report_id}", headers=rep_headers, json={"rep_commentary": "Solid week."})
            check("rep adds commentary", resp.status_code == 200 and resp.json()["rep_commentary"] == "Solid week.", f"HTTP {resp.status_code}")

            resp = await client.post(f"/api/reports/{report_id}/publish", headers=rep_headers)
            check("publish report", resp.status_code == 200 and resp.json()["status"] == "published", f"HTTP {resp.status_code}")

            resp = await client.patch(f"/api/reports/{report_id}", headers=rep_headers, json={"rep_commentary": "Should be locked."})
            check("published report rejects further edits", resp.status_code == 409, f"HTTP {resp.status_code}")

        resp = await client.post("/api/reports/generate", headers=admin_headers, json={})
        check("client_admin blocked from write:reports", resp.status_code == 403, f"HTTP {resp.status_code}")

    await engine.dispose()

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
