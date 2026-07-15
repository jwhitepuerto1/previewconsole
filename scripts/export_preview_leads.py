"""
Manual export of preview-signup leads for hand-import into Mautic, until the
automated push (app/integrations/mautic.py) is working.

Reads platform_audit_log for action='preview_registered' rows and writes a
CSV Mautic's contact importer can consume (map columns during import).

Usage (from inside the api container, where settings already point at
production's platform DB):
    docker compose exec api python scripts/export_preview_leads.py > leads.csv
"""
from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.db.models.platform import PlatformAuditLog
from app.db.session import get_engine


async def main() -> None:
    _, sessionmaker = get_engine(settings.platform_database_url)
    async with sessionmaker() as session:
        rows = (
            await session.execute(
                select(PlatformAuditLog)
                .where(PlatformAuditLog.action == "preview_registered")
                .order_by(PlatformAuditLog.created_at)
            )
        ).scalars().all()

    writer = csv.writer(sys.stdout)
    writer.writerow(["email", "name", "deal_type", "raise_target", "registered_at"])
    for row in rows:
        payload = row.payload or {}
        writer.writerow([
            payload.get("email", ""),
            payload.get("name", ""),
            payload.get("deal_type", ""),
            payload.get("raise_target", ""),
            row.created_at.isoformat(),
        ])


if __name__ == "__main__":
    asyncio.run(main())
