"""
Removes throwaway accounts left behind by verify_phase1.py, verify_phase2.py,
and local SSE testing — real client accounts each with a real provisioned
database, plus their platform_users/platform_support_assignments rows.

Scoped narrowly, matching exactly what those scripts create:
  company_name LIKE 'Phase1 Verify%' OR 'Phase2 Verify%' OR 'SSE Test%'
  email        LIKE 'verify%@%'      OR 'ssetest%@%'
Nothing outside those patterns is touched.

Defaults to a dry run — prints what it would delete without deleting
anything. Pass --confirm to actually execute.

Usage:
    docker compose exec api python scripts/cleanup_test_accounts.py             # dry run
    docker compose exec api python scripts/cleanup_test_accounts.py --confirm   # actually deletes
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.models.platform import (
    PlatformAccount,
    PlatformAuditLog,
    PlatformSupportAssignment,
    PlatformUser,
)
from app.db.session import get_engine

_ACCOUNT_NAME_PATTERNS = ["Phase1 Verify%", "Phase2 Verify%", "SSE Test%"]
_EMAIL_PATTERNS = ["verify%@%", "ssetest%@%"]


async def _drop_database(db_name: str) -> None:
    maintenance_engine = create_async_engine(settings.maintenance_database_url, isolation_level="AUTOCOMMIT")
    try:
        async with maintenance_engine.connect() as conn:
            await conn.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ), {"name": db_name})
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    finally:
        await maintenance_engine.dispose()


async def main() -> None:
    confirm = "--confirm" in sys.argv
    _, sessionmaker = get_engine(settings.platform_database_url)

    async with sessionmaker() as session:
        accounts = (
            await session.execute(
                select(PlatformAccount).where(
                    or_(*(PlatformAccount.company_name.like(p) for p in _ACCOUNT_NAME_PATTERNS))
                )
            )
        ).scalars().all()

        orphan_users = (
            await session.execute(
                select(PlatformUser).where(
                    PlatformUser.client_id.is_(None),
                    or_(*(PlatformUser.email.like(p) for p in _EMAIL_PATTERNS)),
                )
            )
        ).scalars().all()

        print(f"Found {len(accounts)} test account(s):")
        for a in accounts:
            print(f"  - {a.company_name} (id={a.id}, db={a.client_db_name})")
        print(f"Found {len(orphan_users)} client-less test user(s) (cc_admin/support_manager bootstraps):")
        for u in orphan_users:
            print(f"  - {u.email} (role={u.role})")

        if not confirm:
            print("\nDry run only — nothing deleted. Re-run with --confirm to actually delete.")
            return

        for account in accounts:
            if account.client_db_name:
                print(f"Dropping database {account.client_db_name}...")
                await _drop_database(account.client_db_name)
            await session.execute(delete(PlatformSupportAssignment).where(PlatformSupportAssignment.client_id == account.id))
            await session.execute(delete(PlatformUser).where(PlatformUser.client_id == account.id))
            await session.execute(delete(PlatformAuditLog).where(PlatformAuditLog.client_id == account.id))
            await session.delete(account)

        for user in orphan_users:
            await session.execute(delete(PlatformSupportAssignment).where(PlatformSupportAssignment.rep_user_id == user.id))
            await session.delete(user)

        await session.commit()
        print(f"\nDeleted {len(accounts)} account(s) + their databases, and {len(orphan_users)} orphan user(s).")


if __name__ == "__main__":
    asyncio.run(main())
