export interface RegisterResponse {
  token: string;
  profile_db: string;
  profile_name: string;
}

export interface DashboardData {
  raise_name: string | null;
  deal_type: string | null;
  raise_target: number | null;
  days_active: number | null;
  status: string | null;
  investor_count: number;
  pipeline_by_stage: Record<string, number>;
  funding: {
    soft_committed: number;
    hard_committed: number;
    funded: number;
    percent_raised: number;
  };
}

export interface InvestorRow {
  id: string;
  full_name: string;
  company: string;
  title: string;
  investor_type: string;
  fit_score: number;
  stage: string;
  days_in_stage: number;
}

export interface PipelineData {
  investors: InvestorRow[];
}

export interface CampaignsData {
  campaign_name: string | null;
  channel: string | null;
  status: string | null;
  open_rate: number;
  reply_rate: number;
  meetings_scheduled: number;
  weekly_metrics: { week_ending: string | null; sent: number; opened: number; replied: number }[];
}

export interface DataRoomDoc {
  id: string;
  name: string;
  type: string;
  access_level: string;
  uploaded_at: string | null;
}

export interface DataRoomData {
  documents: DataRoomDoc[];
  views_this_week: number;
}

export interface ReportData {
  report_week_ending: string | null;
  key_activities: string | null;
  next_week_priorities: string | null;
  rep_commentary: string | null;
  pipeline_summary: Record<string, unknown>;
  campaign_summary: Record<string, unknown>;
  meeting_summary: Record<string, unknown>;
  funding_summary: Record<string, unknown>;
}

export interface FundingEventRow {
  event_type: string;
  amount: number;
  event_date: string | null;
}

export interface FundingData {
  summary: {
    raise_target: number | null;
    soft_committed: number;
    hard_committed: number;
    funded: number;
    investor_count_soft: number;
    investor_count_funded: number;
    percent_raised: number;
  };
  events: FundingEventRow[];
}

export interface LoginResponse {
  token: string;
  role: string;
  email: string;
}

export interface TargetRow {
  id: string;
  full_name: string | null;
  email: string | null;
  company: string | null;
  title: string | null;
  investor_type: string | null;
  fit_score: number | null;
  status: string | null;
}

export interface PipelineHistoryEntry {
  from_stage: string | null;
  to_stage: string | null;
  moved_by: string | null;
  moved_at: string | null;
  reason: string | null;
}

// ── Real (non-preview) Phase 2/3 shapes — these are per-record lists, not
// the single flattened summary objects the preview routes return above. ──

export interface RealCampaign {
  id: string;
  campaign_name: string | null;
  channel: string | null;
  smartlead_campaign_id: string | null;
  status: string | null;
  start_date: string | null;
  end_date: string | null;
  target_count: number | null;
}

export interface RealDocument {
  id: string;
  document_name: string | null;
  document_type: string | null;
  file_path: string | null;
  file_size_bytes: number | null;
  version: number;
  access_level: string | null;
  uploaded_by: string | null;
  uploaded_at: string;
}

export interface RealFundingSummary {
  raise_target: number | null;
  soft_committed: number;
  hard_committed: number;
  funded: number;
  investor_count_soft: number;
  investor_count_funded: number;
  percent_raised: number;
}

export interface RealFundingEvent {
  id: string;
  investor_target_id: string | null;
  event_type: string | null;
  amount: number | null;
  event_date: string | null;
  notes: string | null;
}

export interface RealReport {
  id: string;
  report_week_ending: string | null;
  generated_at: string;
  generated_by: string | null;
  pipeline_summary: Record<string, unknown> | null;
  campaign_summary: Record<string, unknown> | null;
  meeting_summary: Record<string, unknown> | null;
  funding_summary: Record<string, unknown> | null;
  key_activities: string | null;
  next_week_priorities: string | null;
  rep_commentary: string | null;
  status: string | null;
  published_at: string | null;
}

export interface AlertRow {
  id: string;
  alert_type: string | null;
  severity: string | null;
  title: string | null;
  message: string | null;
  related_investor_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface MeetingRow {
  id: string;
  investor_target_id: string | null;
  meeting_type: string | null;
  scheduled_at: string | null;
  duration_minutes: number | null;
  participants: string[] | null;
  location_or_link: string | null;
  status: string | null;
  outcome: string | null;
  next_step: string | null;
  next_step_date: string | null;
}

export interface ActionItemRow {
  id: string;
  meeting_id: string | null;
  action: string | null;
  assigned_to: string | null;
  due_date: string | null;
  completed: boolean;
  completed_at: string | null;
}

export interface NoteRow {
  id: string;
  investor_target_id: string | null;
  note_type: string | null;
  note: string | null;
  logged_by: string | null;
  logged_at: string;
}

export interface SupportClientHealth {
  client_id: string;
  company_name: string | null;
  status: string | null;
  raise_name: string | null;
  raise_status: string | null;
  investor_count: number;
  percent_raised: number;
  days_since_last_movement: number | null;
  active_campaign_count: number;
  needs_attention: boolean;
  is_escalated: boolean;
}

export interface SupportOverview {
  total_clients: number;
  needs_attention_count: number;
  escalated_count: number;
  average_percent_raised: number;
  clients: SupportClientHealth[];
}

export interface SupportAlertRow {
  client_id: string;
  company_name: string | null;
  id: string;
  alert_type: string | null;
  severity: string | null;
  title: string | null;
  message: string | null;
  is_read: boolean;
  created_at: string;
}
