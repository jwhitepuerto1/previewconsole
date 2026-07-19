"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { escalateClient, getSupportOverview, resolveEscalation } from "@/lib/api";
import { setActingClientId } from "@/lib/auth";
import type { SupportOverview } from "@/lib/types";

export default function SupportOverviewPage() {
  const router = useRouter();
  const [data, setData] = useState<SupportOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reasonById, setReasonById] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  function load() {
    getSupportOverview().then(setData).catch(() => setError("Could not load support overview."));
  }

  useEffect(load, []);

  async function handleEscalate(clientId: string) {
    setBusyId(clientId);
    try {
      await escalateClient(clientId, reasonById[clientId] || "Flagged for senior review.");
      load();
    } finally {
      setBusyId(null);
    }
  }

  async function handleResolve(clientId: string) {
    setBusyId(clientId);
    try {
      await resolveEscalation(clientId);
      load();
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!data) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Cross-Client Overview</h1>

      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <p className="label">Assigned clients</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{data.total_clients}</p>
        </div>
        <div className="card">
          <p className="label">Needs attention</p>
          <p className="mt-1 text-xl font-semibold text-amber-400">{data.needs_attention_count}</p>
        </div>
        <div className="card">
          <p className="label">Escalated</p>
          <p className="mt-1 text-xl font-semibold text-red-400">{data.escalated_count}</p>
        </div>
        <div className="card">
          <p className="label">Average % raised</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{(data.average_percent_raised * 100).toFixed(1)}%</p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {data.clients.length === 0 ? (
          <p className="text-sm text-slate-300">No clients assigned yet.</p>
        ) : (
          data.clients.map((c) => (
            <div key={c.client_id} className="card flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-100">{c.raise_name ?? c.company_name}</p>
                <p className="text-xs text-slate-300">
                  {c.investor_count} investors · {(c.percent_raised * 100).toFixed(1)}% raised ·{" "}
                  {c.days_since_last_movement == null ? "no pipeline activity yet" : `${c.days_since_last_movement}d since last move`}
                  {" "}· {c.active_campaign_count} active campaigns
                </p>
              </div>
              <div className="flex items-center gap-2">
                {c.needs_attention && !c.is_escalated && <span className="label text-amber-400">Needs attention</span>}
                {c.is_escalated ? (
                  <button
                    onClick={() => handleResolve(c.client_id)}
                    disabled={busyId === c.client_id}
                    className="rounded-lg border border-red-800 px-3 py-1.5 text-sm text-red-400 hover:bg-red-950 disabled:opacity-50"
                  >
                    Escalated — resolve
                  </button>
                ) : (
                  <>
                    <input
                      value={reasonById[c.client_id] ?? ""}
                      onChange={(e) => setReasonById((prev) => ({ ...prev, [c.client_id]: e.target.value }))}
                      placeholder="Escalation reason…"
                      className="w-56 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-brand-accent"
                    />
                    <button
                      onClick={() => handleEscalate(c.client_id)}
                      disabled={busyId === c.client_id}
                      className="rounded-lg border border-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-900 disabled:opacity-50"
                    >
                      Flag
                    </button>
                  </>
                )}
                <button
                  onClick={() => { setActingClientId(c.client_id); router.push("/dashboard"); }}
                  className="rounded-lg border border-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-900"
                >
                  View raise
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
