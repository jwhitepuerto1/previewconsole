"""
FastAPI dependency wrapping permissions.py's role matrix. This pass is the
first to actually enforce it — middleware/auth.py sets request.state.role,
this dependency checks it against the permission a route requires.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.permissions import has_permission


def require_permission(*permissions: str):
    """Passes if the role has ANY of the given permissions — needed because
    the matrix uses different tokens for conceptually-similar access across
    roles (e.g. client_admin's "read:own_raise" vs support_manager's
    "read:all_assigned_clients" both mean "can view this raise's dashboard")."""
    def dependency(request: Request) -> None:
        role = request.state.role
        if not role:
            raise HTTPException(status_code=401, detail="Authentication required.")
        if not any(has_permission(role, p) for p in permissions):
            raise HTTPException(status_code=403, detail=f"Role '{role}' lacks permission: {', '.join(permissions)}.")

    return dependency
