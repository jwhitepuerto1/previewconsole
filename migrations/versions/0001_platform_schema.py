"""Platform DB schema — 4 tables (CLAUDE_CRM_MODULE.md section 6).

Revision ID: 0001_platform_schema
Revises:
Create Date: 2026-07-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_platform_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.Text()),
        sa.Column("primary_contact_name", sa.Text()),
        sa.Column("primary_contact_email", sa.Text()),
        sa.Column("deal_type", sa.String(100)),
        sa.Column("raise_target_amount", sa.BigInteger()),
        sa.Column("client_db_name", sa.Text()),
        sa.Column("client_db_url", sa.Text()),
        sa.Column("status", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "platform_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text()),
        sa.Column("full_name", sa.Text()),
        sa.Column("role", sa.String(50)),
        sa.Column("client_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "platform_support_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rep_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("client_id", postgresql.UUID(as_uuid=True)),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        "platform_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("user_role", sa.String(50)),
        sa.Column("client_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(255)),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in ["platform_audit_log", "platform_support_assignments", "platform_users", "platform_accounts"]:
        op.drop_table(table)
