"""
Role permission matrix, verbatim from CLAUDE_CRM_MODULE.md section 5.
Only "preview" is actually enforced by any route/middleware in this pass —
the rest is here so the matrix doesn't need to be reconstructed when the
other 5 roles' real login flows are built.
"""
from __future__ import annotations

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "cc_admin": ["*"],
    "support_manager": [
        "read:all_assigned_clients",
        "write:pipeline", "write:campaigns", "write:meetings",
        "write:data_room", "write:onboarding", "write:funding",
        "write:targets", "write:reports", "write:notes",
        "read:alerts", "write:alerts",
        "read:support_dashboard",
    ],
    "client_admin": [
        "read:own_raise", "write:pipeline", "write:meetings",
        "read:campaigns", "read:data_room", "write:data_room",
        "read:onboarding", "read:funding", "read:reports",
        "write:team_members", "write:settings",
    ],
    "client_team": [
        "read:own_raise", "write:pipeline", "write:meetings",
        "read:campaigns", "read:data_room", "read:onboarding",
        "read:funding", "read:reports",
    ],
    "client_readonly": [
        "read:portal", "read:data_room_approved", "read:reports_summary",
    ],
    "preview": [
        "read:preview_only",
    ],
}


def has_permission(role: str, permission: str) -> bool:
    grants = ROLE_PERMISSIONS.get(role, [])
    return "*" in grants or permission in grants
