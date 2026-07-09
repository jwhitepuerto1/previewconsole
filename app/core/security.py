"""
JWT encode/decode + password hashing for the CRM module.
Claim shapes follow CLAUDE_CRM_MODULE.md section 9 exactly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


class TokenError(Exception):
    pass


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def create_preview_token(name: str, email: str, deal_type: str, raise_target: int, client_db: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),  # preview_session_id
        "email": email,
        "name": name,
        "role": "preview",
        "client_id": "preview",
        "client_db": client_db,
        "deal_type": deal_type,
        "raise_target": raise_target,
        "is_preview": True,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_preview_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_client_token(user_id: uuid.UUID, email: str, role: str, client_id: uuid.UUID, client_db: str) -> str:
    """role is client_admin | client_team | client_readonly — a single-client token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "client_id": str(client_id),
        "client_db": client_db,
        "is_preview": False,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_support_token(user_id: uuid.UUID, email: str, role: str, assigned_clients: list[str]) -> str:
    """role is support_manager | cc_admin — no single client_id; client_db_url is
    resolved per-request from the X-Acting-Client-Id header instead (see
    middleware/auth.py). cc_admin's assigned_clients is conventionally empty —
    its access isn't list-driven, permissions.py grants it "*"."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "client_id": None,
        "assigned_clients": assigned_clients,
        "is_preview": False,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc
