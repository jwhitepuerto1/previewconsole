"use client";

import { useEffect, useState } from "react";
import { getSupportAlerts } from "@/lib/api";
import type { SupportAlertRow } from "@/lib/types";

export default function SupportAlertsPage() {
  const [alerts, setAlerts] = useState<SupportAlertRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSupportAlerts().then((res) => setAlerts(res.alerts)).catch(() => setError("Could not load alerts."));
  }, []);

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!alerts) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Alert Center — All Assigned Clients</h1>

      {alerts.length === 0 ? (
        <p className="text-sm text-slate-300">No alerts across your assigned clients yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {alerts.map((a) => (
            <div key={a.id} className={`card ${a.is_read ? "" : "border-brand-accent"}`}>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-100">{a.title}</p>
                <span className="label">{a.company_name}</span>
              </div>
              <p className="mt-1 text-sm text-slate-300">{a.message}</p>
              <p className="mt-1 text-xs text-slate-300">{new Date(a.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
