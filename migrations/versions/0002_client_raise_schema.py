"""Client-raise DB schema — 28 tables (CLAUDE_CRM_MODULE.md section 7).

Applied identically to real per-client DBs (future) and, this pass, to the
3 preview databases as pristine unmodified copies of the same schema.

Independent revision tree from 0001_platform_schema (down_revision=None
here too, deliberately not chained) — this schema is only ever applied to
preview/client databases, never to the platform database, so a shared
linear history would be wrong (upgrading a client DB to "head" would also
try to create platform tables in it).

Revision ID: 0002_client_raise_schema
Revises:
Create Date: 2026-07-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_client_raise_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raise_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True)),
        sa.Column("raise_name", sa.Text()),
        sa.Column("deal_type", sa.String(100)),
        sa.Column("asset_class", sa.String(100)),
        sa.Column("geography", sa.Text()),
        sa.Column("raise_target", sa.BigInteger()),
        sa.Column("minimum_investment", sa.BigInteger()),
        sa.Column("structure", sa.String(100)),
        sa.Column("launch_date", sa.Date()),
        sa.Column("target_close_date", sa.Date()),
        sa.Column("status", sa.String(50)),
        sa.Column("d_and_d_handoff_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "investor_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("universe_person_id", postgresql.UUID(as_uuid=True)),
        sa.Column("full_name", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("linkedin_url", sa.Text()),
        sa.Column("title", sa.Text()),
        sa.Column("company", sa.Text()),
        sa.Column("investor_type", sa.String(100)),
        sa.Column("geography", sa.Text()),
        sa.Column("fit_score", sa.Integer()),
        sa.Column("status", sa.String(100)),
        sa.Column("added_by", sa.String(255)),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "pipeline_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("stage", sa.String(100)),
        sa.Column("previous_stage", sa.String(100)),
        sa.Column("stage_entered_at", sa.DateTime(timezone=True)),
        sa.Column("stage_updated_by", sa.String(255)),
        sa.Column("days_in_stage", sa.Integer()),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "pipeline_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("from_stage", sa.String(100)),
        sa.Column("to_stage", sa.String(100)),
        sa.Column("moved_by", sa.String(255)),
        sa.Column("moved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reason", sa.Text()),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_name", sa.Text()),
        sa.Column("channel", sa.String(50)),
        sa.Column("smartlead_campaign_id", sa.Text()),
        sa.Column("mautic_campaign_id", sa.Text()),
        sa.Column("status", sa.String(50)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("target_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "email_sequence_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(100)),
        sa.Column("event_at", sa.DateTime(timezone=True)),
        sa.Column("subject_line", sa.Text()),
        sa.Column("sequence_step", sa.Integer()),
        sa.Column("smartlead_event_id", sa.Text()),
        sa.Column("raw_payload", postgresql.JSONB()),
    )

    op.create_table(
        "campaign_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metric_date", sa.Date()),
        sa.Column("sent_count", sa.Integer()),
        sa.Column("delivered_count", sa.Integer()),
        sa.Column("open_count", sa.Integer()),
        sa.Column("click_count", sa.Integer()),
        sa.Column("reply_count", sa.Integer()),
        sa.Column("bounce_count", sa.Integer()),
        sa.Column("unsubscribe_count", sa.Integer()),
        sa.Column("open_rate", sa.Float()),
        sa.Column("reply_rate", sa.Float()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "linkedin_touchpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("touchpoint_type", sa.String(100)),
        sa.Column("content_summary", sa.Text()),
        sa.Column("sent_by", sa.String(255)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("response_received", sa.Boolean(), server_default=sa.false()),
        sa.Column("response_summary", sa.Text()),
        sa.Column("response_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("meeting_type", sa.String(100)),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("participants", postgresql.ARRAY(sa.Text())),
        sa.Column("location_or_link", sa.Text()),
        sa.Column("status", sa.String(50)),
        sa.Column("notes", sa.Text()),
        sa.Column("outcome", sa.String(100)),
        sa.Column("next_step", sa.Text()),
        sa.Column("next_step_date", sa.Date()),
        sa.Column("logged_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "meeting_action_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.Text()),
        sa.Column("assigned_to", sa.String(255)),
        sa.Column("due_date", sa.Date()),
        sa.Column("completed", sa.Boolean(), server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "investor_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("note_type", sa.String(50)),
        sa.Column("note", sa.Text()),
        sa.Column("logged_by", sa.String(255)),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "investor_objections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("objection_type", sa.String(100)),
        sa.Column("objection_detail", sa.Text()),
        sa.Column("response_given", sa.Text()),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false()),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "investor_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("preference_type", sa.String(100)),
        sa.Column("preference_value", sa.Text()),
        sa.Column("source", sa.String(50)),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "data_room_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_name", sa.Text()),
        sa.Column("document_type", sa.String(100)),
        sa.Column("file_path", sa.Text()),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("access_level", sa.String(50)),
        sa.Column("uploaded_by", sa.String(255)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        "data_room_access_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("accessed_by", sa.String(255)),
        sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("access_duration_seconds", sa.Integer()),
        sa.Column("ip_address", sa.Text()),
    )

    op.create_table(
        "onboarding_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("investment_amount", sa.BigInteger()),
        sa.Column("structure", sa.String(100)),
        sa.Column("status", sa.String(100)),
        sa.Column("kyc_provider", sa.String(100)),
        sa.Column("kyc_reference", sa.Text()),
        sa.Column("kyc_completed_at", sa.DateTime(timezone=True)),
        sa.Column("subscription_doc_sent_at", sa.DateTime(timezone=True)),
        sa.Column("subscription_doc_signed_at", sa.DateTime(timezone=True)),
        sa.Column("accreditation_verified_at", sa.DateTime(timezone=True)),
        sa.Column("north_capital_reference", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "onboarding_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("onboarding_record_id", postgresql.UUID(as_uuid=True)),
        sa.Column("item_name", sa.Text()),
        sa.Column("item_type", sa.String(100)),
        sa.Column("status", sa.String(50)),
        sa.Column("due_date", sa.Date()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "funding_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("onboarding_record_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(50)),
        sa.Column("amount", sa.BigInteger()),
        sa.Column("event_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("logged_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "funding_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("raise_target", sa.BigInteger()),
        sa.Column("soft_committed", sa.BigInteger(), server_default="0"),
        sa.Column("hard_committed", sa.BigInteger(), server_default="0"),
        sa.Column("funded", sa.BigInteger(), server_default="0"),
        sa.Column("investor_count_soft", sa.Integer(), server_default="0"),
        sa.Column("investor_count_funded", sa.Integer(), server_default="0"),
        sa.Column("percent_raised", sa.Float(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "weekly_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_week_ending", sa.Date()),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("generated_by", sa.String(100)),
        sa.Column("pipeline_summary", postgresql.JSONB()),
        sa.Column("campaign_summary", postgresql.JSONB()),
        sa.Column("meeting_summary", postgresql.JSONB()),
        sa.Column("funding_summary", postgresql.JSONB()),
        sa.Column("key_activities", sa.Text()),
        sa.Column("next_week_priorities", sa.Text()),
        sa.Column("rep_commentary", sa.Text()),
        sa.Column("status", sa.String(50)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "raise_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_type", sa.String(100)),
        sa.Column("severity", sa.String(20)),
        sa.Column("title", sa.Text()),
        sa.Column("message", sa.Text()),
        sa.Column("related_investor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false()),
        sa.Column("read_by", sa.String(255)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rep_activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rep_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("activity_type", sa.String(100)),
        sa.Column("description", sa.Text()),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raise_timeline",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100)),
        sa.Column("event_description", sa.Text()),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_client_visible", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reengagement_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("decline_reason", sa.String(100)),
        sa.Column("decline_date", sa.Date()),
        sa.Column("reengagement_eligible", sa.Boolean(), server_default=sa.true()),
        sa.Column("reengagement_after", sa.Date()),
        sa.Column("future_raise_fit", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ir_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investor_target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("preferred_update_frequency", sa.String(50)),
        sa.Column("preferred_format", sa.String(50)),
        sa.Column("communication_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ir_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("update_type", sa.String(100)),
        sa.Column("period_covered", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("sent_to_count", sa.Integer()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(255)),
    )

    op.create_table(
        "client_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("title", sa.Text()),
        sa.Column("role", sa.String(50)),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raise_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("user_role", sa.String(50)),
        sa.Column("action", sa.String(255)),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("before_state", postgresql.JSONB()),
        sa.Column("after_state", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "raise_audit_log", "client_contacts", "ir_updates", "ir_preferences",
        "reengagement_candidates", "raise_timeline", "rep_activity_log", "raise_alerts",
        "weekly_reports", "funding_summary", "funding_events", "onboarding_checklist_items",
        "onboarding_records", "data_room_access_log", "data_room_documents",
        "investor_preferences", "investor_objections", "investor_notes",
        "meeting_action_items", "meetings", "linkedin_touchpoints", "campaign_metrics",
        "email_sequence_events", "campaigns", "pipeline_history", "pipeline_records",
        "investor_targets", "raise_config",
    ]:
        op.drop_table(table)
