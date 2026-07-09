"""
Real per-client database provisioning — CREATE DATABASE + apply the
client-raise schema migration. Called by api/routes/accounts.py on account
creation.

Runs the actual Alembic migration (0002_client_raise_schema), not
Base.metadata.create_all() — that migration is already the deliberately
single source of truth for this schema, proven against 3 preview databases
today. Running command.upgrade() also stamps alembic_version as a free side
effect, so this DB is correctly positioned for any future migration.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

CRM_DIR = Path(__file__).resolve().parent.parent.parent  # crm/
CLIENT_SCHEMA_REVISION = "0002_client_raise_schema"


class ProvisioningError(Exception):
    pass


def _client_db_url(db_name: str) -> str:
    """Same host/user/password as the platform DB, different dbname —
    built via urlsplit/urlunsplit so the already-%23-encoded password is
    never touched."""
    parts = urlsplit(settings.platform_database_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{db_name}", parts.query, parts.fragment))


def _run_migration(db_url: str) -> None:
    """Sync — Alembic's command.upgrade() internally does asyncio.run(), so
    this must be called via asyncio.to_thread() from an async caller, never
    awaited directly inside a running event loop."""
    cfg = Config(str(CRM_DIR / "alembic.ini"))
    # Absolute path, not the ini's relative "migrations" — same class of
    # CWD-relative-resolution bug hit twice already today (config.py's
    # env_file, migrations/env.py's own DATABASE_URL lookup).
    cfg.set_main_option("script_location", str(CRM_DIR / "migrations"))
    cfg.attributes["target_db_url"] = db_url
    command.upgrade(cfg, CLIENT_SCHEMA_REVISION)


async def provision_client_database(client_id: uuid.UUID) -> tuple[str, str]:
    """Creates ias_crm_client_{id} and applies the client-raise schema.
    Returns (db_name, db_url). Raises ProvisioningError on failure — callers
    should catch this, mark the account provisioning_failed, and leave the
    physical database for manual inspection rather than auto-dropping it."""
    db_name = f"ias_crm_client_{client_id.hex}"
    db_url = _client_db_url(db_name)

    maintenance_engine = create_async_engine(settings.maintenance_database_url, isolation_level="AUTOCOMMIT")
    try:
        async with maintenance_engine.connect() as conn:
            # db_name is server-generated from a uuid, never user input —
            # safe to interpolate; CREATE DATABASE doesn't support bind params.
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except Exception as exc:
        raise ProvisioningError(f"CREATE DATABASE failed for {db_name}: {exc}") from exc
    finally:
        await maintenance_engine.dispose()

    try:
        await asyncio.to_thread(_run_migration, db_url)
    except Exception as exc:
        raise ProvisioningError(f"Migration failed for {db_name} (database was created): {exc}") from exc

    return db_name, db_url
