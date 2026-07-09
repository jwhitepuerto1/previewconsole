"""
Bootstrap/test-user CLI for the platform DB. Not an HTTP route deliberately —
an unauthenticated account-creation endpoint minting cc_admin ("*") access
is not an acceptable attack surface, and would contradict AuthMiddleware's
existing "everything except a 5-path whitelist requires Bearer auth" model.

Usage:
    python crm/scripts/create_platform_user.py --role cc_admin --email admin@capitalcontext.com
    python crm/scripts/create_platform_user.py --role client_admin --email jane@client.com --client-id <uuid>
    python crm/scripts/create_platform_user.py --role support_manager --email rep@capitalcontext.com --assign-client <uuid> --assign-client <uuid2>

Password: interactive getpass by default; set CRM_BOOTSTRAP_PASSWORD to
supply it non-interactively (scripted/CI runs) — never as a bare CLI arg.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.platform import PlatformSupportAssignment, PlatformUser

VALID_ROLES = {"cc_admin", "support_manager", "client_admin", "client_team", "client_readonly"}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a platform user (bootstrap or test).")
    parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", default=None)
    parser.add_argument("--client-id", default=None, help="Required for client_admin/client_team/client_readonly.")
    parser.add_argument("--assign-client", action="append", default=[], help="Repeatable; support_manager only.")
    args = parser.parse_args()

    if args.role in ("client_admin", "client_team", "client_readonly") and not args.client_id:
        parser.error(f"--client-id is required for role {args.role}")

    password = os.environ.get("CRM_BOOTSTRAP_PASSWORD")
    if not password:
        password = getpass.getpass(f"Password for {args.email}: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords did not match.", file=sys.stderr)
            sys.exit(1)

    engine = create_async_engine(settings.platform_database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        existing = (
            await session.execute(select(PlatformUser).where(PlatformUser.email == args.email))
        ).scalar_one_or_none()
        if existing:
            print(f"A user with email {args.email} already exists (id={existing.id}). Aborting.", file=sys.stderr)
            sys.exit(1)

        user = PlatformUser(
            email=args.email,
            hashed_password=hash_password(password),
            full_name=args.full_name or args.email,
            role=args.role,
            client_id=uuid.UUID(args.client_id) if args.client_id else None,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        for client_id in args.assign_client:
            if args.role != "support_manager":
                print("--assign-client is only valid for --role support_manager.", file=sys.stderr)
                sys.exit(1)
            session.add(PlatformSupportAssignment(
                rep_user_id=user.id, client_id=uuid.UUID(client_id), is_active=True,
            ))

        await session.commit()
        print(f"Created {args.role} user: id={user.id} email={user.email}")
        if args.assign_client:
            print(f"Assigned to clients: {args.assign_client}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
