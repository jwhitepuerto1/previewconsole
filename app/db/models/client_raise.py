"""
Per-client raise DB tables — CLAUDE_CRM_MODULE.md section 7.
Applied identically to every ias_crm_client_{id} database (and, this pass,
to the 3 preview databases — see plan decision: preview uses pristine,
unmodified copies of this exact schema, not a shared DB with a discriminator
column). Spec calls this "34 tables" but only enumerates 28 with concrete
columns; built to match exactly what's specified, not padded to 34.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ClientRaiseBase(DeclarativeBase):
    pass


class RaiseConfig(ClientRaiseBase):
    __tablename__ = "raise_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    raise_name: Mapped[str | None] = mapped_column(Text)
    deal_type: Mapped[str | None] = mapped_column(String(100))
    asset_class: Mapped[str | None] = mapped_column(String(100))
    geography: Mapped[str | None] = mapped_column(Text)
    raise_target: Mapped[int | None] = mapped_column(BigInteger)
    minimum_investment: Mapped[int | None] = mapped_column(BigInteger)
    structure: Mapped[str | None] = mapped_column(String(100))  # 506b | 506c | reg_a | other
    launch_date: Mapped[date | None] = mapped_column(Date)
    target_close_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(50))  # pre_launch | active | paused | closed
    d_and_d_handoff_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvestorTarget(ClientRaiseBase):
    __tablename__ = "investor_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    universe_person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    full_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    investor_type: Mapped[str | None] = mapped_column(String(100))
    geography: Mapped[str | None] = mapped_column(Text)
    fit_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(100))  # active | suppressed | removed | invested
    added_by: Mapped[str | None] = mapped_column(String(255))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)


class PipelineRecord(ClientRaiseBase):
    __tablename__ = "pipeline_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # prospect | qualified | engaged | meeting_scheduled | meeting_completed |
    # soft_committed | committed | onboarding | funded | declined | on_hold
    stage: Mapped[str | None] = mapped_column(String(100))
    previous_stage: Mapped[str | None] = mapped_column(String(100))
    stage_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage_updated_by: Mapped[str | None] = mapped_column(String(255))
    days_in_stage: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class PipelineHistory(ClientRaiseBase):
    __tablename__ = "pipeline_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    from_stage: Mapped[str | None] = mapped_column(String(100))
    to_stage: Mapped[str | None] = mapped_column(String(100))
    moved_by: Mapped[str | None] = mapped_column(String(255))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(Text)


class Campaign(ClientRaiseBase):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str | None] = mapped_column(String(50))  # email | linkedin | combined
    smartlead_campaign_id: Mapped[str | None] = mapped_column(Text)
    mautic_campaign_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))  # draft | active | paused | completed
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    target_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EmailSequenceEvent(ClientRaiseBase):
    __tablename__ = "email_sequence_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    event_type: Mapped[str | None] = mapped_column(String(100))  # sent|opened|clicked|replied|bounced|unsubscribed
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subject_line: Mapped[str | None] = mapped_column(Text)
    sequence_step: Mapped[int | None] = mapped_column(Integer)
    smartlead_event_id: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)


class CampaignMetrics(ClientRaiseBase):
    __tablename__ = "campaign_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metric_date: Mapped[date | None] = mapped_column(Date)
    sent_count: Mapped[int | None] = mapped_column(Integer)
    delivered_count: Mapped[int | None] = mapped_column(Integer)
    open_count: Mapped[int | None] = mapped_column(Integer)
    click_count: Mapped[int | None] = mapped_column(Integer)
    reply_count: Mapped[int | None] = mapped_column(Integer)
    bounce_count: Mapped[int | None] = mapped_column(Integer)
    unsubscribe_count: Mapped[int | None] = mapped_column(Integer)
    open_rate: Mapped[float | None] = mapped_column(Float)
    reply_rate: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LinkedinTouchpoint(ClientRaiseBase):
    __tablename__ = "linkedin_touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    touchpoint_type: Mapped[str | None] = mapped_column(String(100))  # connection_request|message|comment|like|inmail
    content_summary: Mapped[str | None] = mapped_column(Text)
    sent_by: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_received: Mapped[bool] = mapped_column(Boolean, default=False)
    response_summary: Mapped[str | None] = mapped_column(Text)
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Meeting(ClientRaiseBase):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    meeting_type: Mapped[str | None] = mapped_column(String(100))  # intro_call|deep_dive|follow_up|diligence|closing
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    participants: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    location_or_link: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))  # scheduled|completed|cancelled|no_show
    notes: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(100))  # positive|neutral|negative|follow_up_required
    next_step: Mapped[str | None] = mapped_column(Text)
    next_step_date: Mapped[date | None] = mapped_column(Date)
    logged_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingActionItem(ClientRaiseBase):
    __tablename__ = "meeting_action_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    due_date: Mapped[date | None] = mapped_column(Date)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InvestorNote(ClientRaiseBase):
    __tablename__ = "investor_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    note_type: Mapped[str | None] = mapped_column(String(50))  # general|objection|preference|follow_up|compliance
    note: Mapped[str | None] = mapped_column(Text)
    logged_by: Mapped[str | None] = mapped_column(String(255))
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvestorObjection(ClientRaiseBase):
    __tablename__ = "investor_objections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # timing|deal_size|asset_class|track_record|structure|geography|relationship|other
    objection_type: Mapped[str | None] = mapped_column(String(100))
    objection_detail: Mapped[str | None] = mapped_column(Text)
    response_given: Mapped[str | None] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvestorPreference(ClientRaiseBase):
    __tablename__ = "investor_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    preference_type: Mapped[str | None] = mapped_column(String(100))
    preference_value: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(50))  # meeting | email | linkedin | rep_note
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DataRoomDocument(ClientRaiseBase):
    __tablename__ = "data_room_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_name: Mapped[str | None] = mapped_column(Text)
    # ppm|exec_summary|financial_model|subscription_agreement|operating_agreement|
    # track_record|market_analysis|team_bios|other
    document_type: Mapped[str | None] = mapped_column(String(100))
    file_path: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(Integer, default=1)
    access_level: Mapped[str | None] = mapped_column(String(50))  # public|qualified|committed|restricted
    uploaded_by: Mapped[str | None] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DataRoomAccessLog(ClientRaiseBase):
    __tablename__ = "data_room_access_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    accessed_by: Mapped[str | None] = mapped_column(String(255))
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    access_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(Text)


class OnboardingRecord(ClientRaiseBase):
    __tablename__ = "onboarding_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    investment_amount: Mapped[int | None] = mapped_column(BigInteger)
    structure: Mapped[str | None] = mapped_column(String(100))  # equity | debt | preferred | other
    # initiated|kyc_pending|kyc_complete|docs_sent|docs_signed|
    # accreditation_pending|accreditation_complete|funded
    status: Mapped[str | None] = mapped_column(String(100))
    kyc_provider: Mapped[str | None] = mapped_column(String(100))
    kyc_reference: Mapped[str | None] = mapped_column(Text)
    kyc_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_doc_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_doc_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accreditation_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    north_capital_reference: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OnboardingChecklistItem(ClientRaiseBase):
    __tablename__ = "onboarding_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    onboarding_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    item_name: Mapped[str | None] = mapped_column(Text)
    item_type: Mapped[str | None] = mapped_column(String(100))  # kyc|accreditation|subscription_doc|wire_instructions|other
    status: Mapped[str | None] = mapped_column(String(50))  # pending|sent|received|verified|waived
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class FundingEvent(ClientRaiseBase):
    __tablename__ = "funding_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    onboarding_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    event_type: Mapped[str | None] = mapped_column(String(50))  # soft_commit|hard_commit|wire_sent|wire_received|funded|returned
    amount: Mapped[int | None] = mapped_column(BigInteger)
    event_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    logged_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FundingSummary(ClientRaiseBase):
    """Single row per raise, maintained in real-time."""
    __tablename__ = "funding_summary"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raise_target: Mapped[int | None] = mapped_column(BigInteger)
    soft_committed: Mapped[int] = mapped_column(BigInteger, default=0)
    hard_committed: Mapped[int] = mapped_column(BigInteger, default=0)
    funded: Mapped[int] = mapped_column(BigInteger, default=0)
    investor_count_soft: Mapped[int] = mapped_column(Integer, default=0)
    investor_count_funded: Mapped[int] = mapped_column(Integer, default=0)
    percent_raised: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WeeklyReport(ClientRaiseBase):
    __tablename__ = "weekly_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_week_ending: Mapped[date | None] = mapped_column(Date)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    generated_by: Mapped[str | None] = mapped_column(String(100))  # system | rep
    pipeline_summary: Mapped[dict | None] = mapped_column(JSONB)
    campaign_summary: Mapped[dict | None] = mapped_column(JSONB)
    meeting_summary: Mapped[dict | None] = mapped_column(JSONB)
    funding_summary: Mapped[dict | None] = mapped_column(JSONB)
    key_activities: Mapped[str | None] = mapped_column(Text)
    next_week_priorities: Mapped[str | None] = mapped_column(Text)
    rep_commentary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))  # draft | published
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RaiseAlert(ClientRaiseBase):
    __tablename__ = "raise_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # pipeline_movement|meeting_scheduled|reply_received|document_accessed|
    # funding_event|onboarding_update|campaign_milestone|rep_note
    alert_type: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str | None] = mapped_column(String(20))  # info | warning | action_required
    title: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    related_investor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_by: Mapped[str | None] = mapped_column(String(255))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RepActivityLog(ClientRaiseBase):
    __tablename__ = "rep_activity_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rep_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    activity_type: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RaiseTimeline(ClientRaiseBase):
    __tablename__ = "raise_timeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str | None] = mapped_column(String(100))
    event_description: Mapped[str | None] = mapped_column(Text)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReengagementCandidate(ClientRaiseBase):
    __tablename__ = "reengagement_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decline_reason: Mapped[str | None] = mapped_column(String(100))
    decline_date: Mapped[date | None] = mapped_column(Date)
    reengagement_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    reengagement_after: Mapped[date | None] = mapped_column(Date)
    future_raise_fit: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IrPreference(ClientRaiseBase):
    __tablename__ = "ir_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    preferred_update_frequency: Mapped[str | None] = mapped_column(String(50))  # monthly|quarterly|as_needed
    preferred_format: Mapped[str | None] = mapped_column(String(50))  # email | portal | call
    communication_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IrUpdate(ClientRaiseBase):
    __tablename__ = "ir_updates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    update_type: Mapped[str | None] = mapped_column(String(100))
    period_covered: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    sent_to_count: Mapped[int | None] = mapped_column(Integer)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(String(255))


class ClientContact(ClientRaiseBase):
    __tablename__ = "client_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(50))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RaiseAuditLog(ClientRaiseBase):
    __tablename__ = "raise_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_role: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str | None] = mapped_column(String(255))
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before_state: Mapped[dict | None] = mapped_column(JSONB)
    after_state: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
