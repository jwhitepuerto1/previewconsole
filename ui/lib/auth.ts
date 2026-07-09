// A single token slot serves both preview and real sessions — they're
// mutually exclusive in one browser tab (you're either previewing or
// logged in for real, never both), so there's no need for separate keys.
const TOKEN_KEY = "crm_token";
const ROLE_KEY = "crm_role";
const PROFILE_NAME_KEY = "crm_preview_profile_name";
const ACTING_CLIENT_KEY = "crm_acting_client_id";

export function storeSession(token: string, profileName: string) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(PROFILE_NAME_KEY, profileName);
  sessionStorage.setItem(ROLE_KEY, "preview");
}

export function storeRealSession(token: string, role: string) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(ROLE_KEY, role);
  sessionStorage.removeItem(PROFILE_NAME_KEY);
  sessionStorage.removeItem(ACTING_CLIENT_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getRole(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ROLE_KEY);
}

export function getProfileName(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(PROFILE_NAME_KEY);
}

export function getActingClientId(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ACTING_CLIENT_KEY);
}

export function setActingClientId(clientId: string) {
  sessionStorage.setItem(ACTING_CLIENT_KEY, clientId);
}

// support_manager/cc_admin need X-Acting-Client-Id on every real-portal
// request; client_admin/client_team/client_readonly tokens carry a single
// client_id already, so the header is a harmless no-op for them server-side.
export function needsActingClientId(): boolean {
  const role = getRole();
  return role === "support_manager" || role === "cc_admin";
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(ROLE_KEY);
  sessionStorage.removeItem(PROFILE_NAME_KEY);
  sessionStorage.removeItem(ACTING_CLIENT_KEY);
}
