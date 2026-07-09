import { getActingClientId, getToken, needsActingClientId } from "./auth";
import type {
  CampaignsData, DashboardData, DataRoomData, FundingData, LoginResponse, PipelineData,
  PipelineHistoryEntry, RegisterResponse, ReportData, TargetRow,
} from "./types";

async function authedGet<T>(path: string): Promise<T> {
  const token = getToken();
  const res = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

// Real (/api/*, non-preview) requests additionally need X-Acting-Client-Id
// for support_manager/cc_admin — a harmless no-op header for client_admin/
// client_team/client_readonly tokens, which already carry a single client_id.
function realHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { ...extra };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (needsActingClientId()) {
    const clientId = getActingClientId();
    if (clientId) headers["X-Acting-Client-Id"] = clientId;
  }
  return headers;
}

async function realFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: { ...realHeaders(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${options.method ?? "GET"} ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export async function register(
  name: string,
  email: string,
  dealType: string,
  raiseTarget: number,
): Promise<RegisterResponse> {
  const res = await fetch("/api/preview/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, deal_type: dealType, raise_target: raiseTarget }),
  });
  if (!res.ok) throw new Error(`register -> ${res.status}`);
  return res.json() as Promise<RegisterResponse>;
}

export async function track(eventType: "page_visit" | "cta_click", detail?: string) {
  const token = getToken();
  if (!token) return;
  await fetch("/api/preview/track", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ event_type: eventType, detail }),
  }).catch(() => {});
}

export const getDashboard = () => authedGet<DashboardData>("/api/preview/dashboard");
export const getPipeline = () => authedGet<PipelineData>("/api/preview/pipeline");
export const getCampaigns = () => authedGet<CampaignsData>("/api/preview/campaigns");
export const getDataRoom = () => authedGet<DataRoomData>("/api/preview/data-room");
export const getReport = () => authedGet<ReportData>("/api/preview/reports");
export const getFunding = () => authedGet<FundingData>("/api/preview/funding");

// ── Real (non-preview) portal ────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`login -> ${res.status}`);
  return res.json() as Promise<LoginResponse>;
}

export const getRealDashboard = () => realFetch<DashboardData>("/api/dashboard");
export const getRealPipeline = () => realFetch<PipelineData>("/api/pipeline");
export const getTargets = () => realFetch<TargetRow[]>("/api/targets");

export const createTarget = (body: {
  full_name: string; email?: string; company?: string; title?: string;
  investor_type?: string; fit_score?: number;
}) => realFetch<TargetRow>("/api/targets", { method: "POST", body: JSON.stringify(body) });

export const patchPipelineStage = (targetId: string, stage: string, reason?: string) =>
  realFetch<{ investor_target_id: string; from_stage: string; to_stage: string }>(
    `/api/pipeline/${targetId}/stage`,
    { method: "PATCH", body: JSON.stringify({ stage, reason }) },
  );

export const getPipelineHistory = (targetId: string) =>
  realFetch<{ history: PipelineHistoryEntry[] }>(`/api/pipeline/${targetId}/history`);
