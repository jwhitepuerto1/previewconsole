"""
Startup configuration and environment validation for the CRM module.
Missing required vars raise on boot, not at first request.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path, not "​.env" — pydantic-settings resolves a relative env_file
# against the process's CWD, not this file's location. Launching via
# `uvicorn app.main:app --app-dir crm` (needed to avoid colliding with the
# root app.* package) runs with CWD = repo root, not crm/, which would
# silently load the wrong .env (or none) if this were left relative.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # Platform + preview databases
    platform_database_url: str
    preview_database_url_meridian: str
    preview_database_url_cornerstone: str
    preview_database_url_elevation: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_preview_expire_minutes: int = 240
    jwt_access_expire_minutes: int = 480

    environment: str = "development"

    # Mautic (preview-signup lead push — see app/integrations/mautic.py)
    mautic_base_url: str = ""
    mautic_client_id: str = ""
    mautic_client_secret: str = ""
    mautic_redirect_uri: str = ""
    mautic_segment_id: int | None = None

    @property
    def debug(self) -> bool:
        return self.environment == "development"

    @property
    def preview_db_map(self) -> dict[str, str]:
        """deal_type -> preview DB name (not URL — the name is what goes in the
        JWT's client_db claim; middleware resolves name -> URL -> engine)."""
        return {
            "cre_syndication": "ias_crm_preview_meridian",
            "private_credit": "ias_crm_preview_cornerstone",
            "real_estate_fund": "ias_crm_preview_elevation",
            "other": "ias_crm_preview_elevation",
        }

    @property
    def maintenance_database_url(self) -> str:
        """platform_database_url with the dbname swapped to "postgres" — used
        to CREATE DATABASE (which cannot run against a DB it would drop/alter,
        and Postgres has no dedicated maintenance-only role requirement, just
        needs a DB connection that already exists). Uses urlsplit/urlunsplit,
        not string replace, so the already-%23-encoded password in the
        netloc is never touched."""
        parts = urlsplit(self.platform_database_url)
        return urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))

    @property
    def preview_db_urls(self) -> dict[str, str]:
        """preview DB name -> connection URL, used by both the register route
        (to pick a DB) and auth middleware (to resolve request.state.client_db_url)."""
        return {
            "ias_crm_preview_meridian": self.preview_database_url_meridian,
            "ias_crm_preview_cornerstone": self.preview_database_url_cornerstone,
            "ias_crm_preview_elevation": self.preview_database_url_elevation,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Eagerly validate on import — crash at startup, not at first request
settings = get_settings()
