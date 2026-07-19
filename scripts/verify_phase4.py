"""
Phase 4 production smoke test — support dashboard cross-client aggregation
(overview, clients, alerts) and the escalation flag system, same style as
verify_phase1-3.py. Provisions TWO real client accounts to actually
exercise the cross-client fan-out (asyncio.gather across per-client DBs),
not just a single-client happy path.

Run from inside the deployed api container:
    docker compose exec api python scripts/verify_phase4.py
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
    user = PlatformUser(email=email, hashed_password=hash_password(password), full_name=email, role=role, client_id=client_id, is_active=True)
    session.add(user)
    await session.flush()
    return user.id


async def main() -> None:
    password = secrets.token_urlsafe(16)
    run_id = uuid.uuid4().hex[:8]
    engine = create_async_engine(settings.platform_database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    cc_email = f"verify4-ccadmin-{run_id}@capitalcontext.internal"
    async with Session() as session:
        await create_user(session, cc_email, "cc_admin", None, password)
        await session.commit()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post("/auth/login", json={"email": cc_email, "password": password})
        check("cc_admin login", resp.status_code == 200, f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            return
        cc_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        client_ids = []
        for n in (1, 2):
            resp = await client.post("/api/accounts", headers=cc_headers, json={
                "company_name": f"Phase4 Verify {run_id}-{n}", "primary_contact_name": "Verify Bot",
                "primary_contact_email": f"verify4-client{n}-{run_id}@capitalcontext.internal",
                "deal_type": "cre_syndication", "raise_target_amount": 1000000,
            })
            check(f"POST /api/accounts #{n} (provisions client DB)", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")
            if resp.status_code != 200:
                return
            client_ids.append(resp.json()["id"])

        rep_email = f"verify4-rep-{run_id}@capitalcontext.internal"
        async with Session() as session:
            rep_id = await create_user(session, rep_email, "support_manager", None, password)
            for cid in client_ids:
                session.add(PlatformSupportAssignment(rep_user_id=rep_id, client_id=uuid.UUID(cid), is_active=True))
            await session.commit()

        resp = await client.post("/auth/login", json={"email": rep_email, "password": password})
        check("support_manager login", resp.status_code == 200, f"HTTP {resp.status_code}")
        rep_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

        # Add one target + move its stage in client #1 only, so the two
        # clients' health rows should actually differ from each other.
        rep_headers_1 = {**rep_headers, "X-Acting-Client-Id": client_ids[0]}
        resp = await client.post("/api/targets", headers=rep_headers_1, json={"full_name": "Verify Investor 4", "company": "Test Capital"})
        target_id = resp.json()["id"] if resp.status_code == 200 else None
        if target_id:
            await client.patch(f"/api/pipeline/{target_id}/stage", headers=rep_headers_1, json={"stage": "qualified"})

        resp = await client.get("/api/support/clients", headers=rep_headers)
        clients_by_id = {c["client_id"]: c for c in resp.json().get("clients", [])} if resp.status_code == 200 else {}
        check(
            "GET /api/support/clients returns both assigned clients",
            resp.status_code == 200 and set(clients_by_id) == set(client_ids),
            f"HTTP {resp.status_code}: {clients_by_id}",
        )
        check(
            "client #1 shows the investor + recent movement, client #2 doesn't",
            clients_by_id.get(client_ids[0], {}).get("investor_count") == 1
            and clients_by_id.get(client_ids[0], {}).get("days_since_last_movement") == 0
            and clients_by_id.get(client_ids[1], {}).get("investor_count") == 0,
            f"{clients_by_id}",
        )

        resp = await client.get("/api/support/overview", headers=rep_headers)
        overview = resp.json() if resp.status_code == 200 else {}
        check(
            "GET /api/support/overview aggregates totals across both clients",
            resp.status_code == 200 and overview.get("total_clients") == 2,
            f"HTTP {resp.status_code}: {overview}",
        )

        resp = await client.get("/api/support/alerts", headers=rep_headers)
        alerts = resp.json().get("alerts", []) if resp.status_code == 200 else []
        check(
            "GET /api/support/alerts aggregates alerts across both clients (pipeline_movement from client #1)",
            resp.status_code == 200 and any(a["client_id"] == client_ids[0] and a["alert_type"] == "pipeline_movement" for a in alerts),
            f"HTTP {resp.status_code}: count={len(alerts)}",
        )

        # Escalation flow
        resp = await client.post(f"/api/support/clients/{client_ids[1]}/escalate", headers=rep_headers, json={"reason": "No pipeline activity."})
        check("escalate client #2", resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:150]}")

        resp = await client.get("/api/support/clients", headers=rep_headers)
        clients_by_id = {c["client_id"]: c for c in resp.json().get("clients", [])} if resp.status_code == 200 else {}
        check(
            "client #2 shows is_escalated=True, client #1 does not",
            clients_by_id.get(client_ids[1], {}).get("is_escalated") is True
            and clients_by_id.get(client_ids[0], {}).get("is_escalated") is False,
            f"{clients_by_id}",
        )

        resp = await client.post(f"/api/support/clients/{client_ids[1]}/resolve-escalation", headers=rep_headers)
        check("resolve escalation on client #2", resp.status_code == 200, f"HTTP {resp.status_code}")

        resp = await client.get("/api/support/clients", headers=rep_headers)
        clients_by_id = {c["client_id"]: c for c in resp.json().get("clients", [])} if resp.status_code == 200 else {}
        check(
            "client #2 no longer escalated after resolve",
            clients_by_id.get(client_ids[1], {}).get("is_escalated") is False,
            f"{clients_by_id.get(client_ids[1])}",
        )

    await engine.dispose()

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
