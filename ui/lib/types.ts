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
