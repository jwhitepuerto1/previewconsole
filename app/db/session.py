"""
Multi-database session routing.
Unlike IAM's single hardcoded engine (app/db/session.py at the repo root),
CRM must serve requests against one of several possible databases (platform,
preview x3, and eventually N per-client databases), resolved per-request
from the caller's JWT.

get_engine() is the only seam: it caches an (engine, sessionmaker) pair per
URL. get_platform_db() always resolves the platform database. get_tenant_db()
resolves whatever URL auth middleware already set on request.state.client_db_url
— routes never decode a JWT or pick a database themselves. When real
per-client dynamic routing is added later, only the middleware's URL
resolution changes; this file and every route stay the same.
"""
from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engines: dict[str, tuple[AsyncEngine, async_sessionmaker]] = {}


def get_engine(db_url: str) -> tuple[AsyncEngine, async_sessionmaker]:
    if db_url not in _engines:
        engine = create_async_engine(db_url, echo=False)
        _engines[db_url] = (engine, async_sessionmaker(engine, expire_on_commit=False))
    return _engines[db_url]


async def get_platform_db() -> AsyncSession:
    _, sessionmaker = get_engine(settings.platform_database_url)
    async with sessionmaker() as session:
        yield session


async def get_tenant_db(request: Request) -> AsyncSession:
    db_url = getattr(request.state, "client_db_url", None)
    if not db_url:
        # Preview/client tokens always resolve client_db_url in middleware —
        # reaching here with none set means a cc_admin/support_manager token
        # hit a tenant-DB route without X-Acting-Client-Id (optional at the
        # middleware layer since platform-only routes like POST /api/accounts
        # don't need it — see middleware/auth.py).
        raise HTTPException(status_code=400, detail="X-Acting-Client-Id header is required for this operation.")
    _, sessionmaker = get_engine(db_url)
    async with sessionmaker() as session:
        yield session
