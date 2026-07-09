"""Platform DB — platform_integration_tokens table (outbound OAuth2 refresh
tokens, e.g. Mautic — see app/integrations/mautic.py).

Revision ID: 0003_platform_integration_tokens
Revises: 0001_platform_schema
Create Date: 2026-07-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_platform_integration_tokens"
down_revision = "0001_platform_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_integration_tokens",
        sa.Column("provider", sa.String(50), primary_key=True),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("platform_integration_tokens")
