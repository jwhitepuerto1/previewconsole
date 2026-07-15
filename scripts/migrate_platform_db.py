"""
One-off migration runner for the platform DB, targeting a URL other than
the local one in .env — e.g. running a new migration against production.

The target URL is read from the TARGET_DATABASE_URL environment variable
(set it in your own terminal session, never as a CLI arg) so a production
password never appears in this script's invocation or shell history.

Usage (PowerShell):
    $env:TARGET_DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"
    .venv_iascre\\Scripts\\python.exe crm\\scripts\\migrate_platform_db.py [revision]

`revision` defaults to "head" of the platform-DB tree (currently
0003_platform_integration_tokens).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

CRM_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REVISION = "0003_platform_integration_tokens"


def main() -> None:
    target_url = os.environ.get("TARGET_DATABASE_URL")
    if not target_url:
        print("TARGET_DATABASE_URL is not set in this shell session.", file=sys.stderr)
        sys.exit(1)

    revision = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REVISION

    cfg = Config(str(CRM_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(CRM_DIR / "migrations"))
    cfg.attributes["target_db_url"] = target_url

    print(f"Applying revision {revision}...")
    command.upgrade(cfg, revision)
    print("Done.")


if __name__ == "__main__":
    main()
