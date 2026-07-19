"use client";

import { useEffect, useRef, useState } from "react";
import { getAlerts, markAllAlertsRead, markAlertRead } from "@/lib/api";
import { getActingClientId, getToken, needsActingClientId } from "@/lib/auth";
import type { AlertRow } from "@/lib/types";

// Native EventSource can't send a custom Authorization header, so this reads
// the stream manually via fetch — same technique the backend's own
// verify_phase2.py smoke test uses to prove the SSE fix actually streams.
export function AlertBell() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [open, setOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getAlerts().then(setAlerts).catch(() => {});

    const token = getToken();
    if (!token) return;

    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        // Same acting-client-id requirement as api.ts's realHeaders() —
        // support_manager/cc_admin have no single client_id on their token,
        // so without this the backend has no client context and 400s.
        const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
        if (needsActingClientId()) {
          const clientId = getActingClientId();
          if (clientId) headers["X-Acting-Client-Id"] = clientId;
        }
        const res = await fetch("/api/alerts/stream", {
          headers,
          signal: controller.signal,
        });
        if (!res.body) return;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = JSON.parse(line.slice("data: ".length));
            if (payload.type === "ready") continue;
            setAlerts((prev) => [payload as AlertRow, ...prev]);
          }
        }
      } catch {
        // Connection dropped/aborted — the bell just stops updating live;
        // the next page load's getAlerts() call still shows the latest.
      }
    })();

    return () => controller.abort();
  }, []);

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  async function handleMarkRead(id: string) {
    await markAlertRead(id);
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)));
  }

  async function handleMarkAllRead() {
    await markAllAlertsRead();
    setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-900 hover:text-slate-200"
      >
        Alerts
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] font-semibold text-slate-950">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-10 mt-2 w-96 rounded-xl border border-slate-800 bg-slate-900 p-3 shadow-xl">
          <div className="mb-2 flex items-center justify-between">
            <p className="label">Recent alerts</p>
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="text-xs text-brand-accent hover:underline">
                Mark all read
              </button>
            )}
          </div>
          {alerts.length === 0 ? (
            <p className="text-sm text-slate-300">No alerts yet.</p>
          ) : (
            <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
              {alerts.map((a) => (
                <button
                  key={a.id}
                  onClick={() => !a.is_read && handleMarkRead(a.id)}
                  className={`rounded-lg border border-slate-800 px-3 py-2 text-left text-sm ${
                    a.is_read ? "bg-slate-950 text-slate-300" : "bg-slate-800 text-slate-100"
                  }`}
                >
                  <p className="font-medium">{a.title}</p>
                  <p className="text-xs text-slate-300">{a.message}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
