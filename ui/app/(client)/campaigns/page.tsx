"use client";

import { useEffect, useState } from "react";
import { createCampaign, getRealCampaigns, launchCampaign, pauseCampaign } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { RealCampaign } from "@/lib/types";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<RealCampaign[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [channel, setChannel] = useState("email");
  const [creating, setCreating] = useState(false);

  function load() {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view campaigns.");
      return;
    }
    getRealCampaigns().then(setCampaigns).catch(() => setError("Could not load campaigns."));
  }

  useEffect(load, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createCampaign({ campaign_name: name, channel });
      setName("");
      load();
    } catch {
      setError("Could not create campaign — this role may not have write:campaigns permission.");
    } finally {
      setCreating(false);
    }
  }

  async function handleLaunch(id: string) {
    setBusyId(id);
    try {
      await launchCampaign(id);
      load();
    } catch {
      setError("Could not launch — this role may not have write:campaigns permission.");
    } finally {
      setBusyId(null);
    }
  }

  async function handlePause(id: string) {
    setBusyId(id);
    try {
      await pauseCampaign(id);
      load();
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!campaigns) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Campaigns</h1>

      <form onSubmit={handleCreate} className="card flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Campaign name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
        </div>
        <div>
          <label className="label">Channel</label>
          <select value={channel} onChange={(e) => setChannel(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent">
            <option value="email">Email</option>
            <option value="linkedin">LinkedIn</option>
            <option value="combined">Combined</option>
          </select>
        </div>
        <button type="submit" disabled={creating}
          className="rounded-lg bg-brand-accent px-4 py-2 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50">
          {creating ? "Creating…" : "Create campaign"}
        </button>
      </form>

      {campaigns.length === 0 ? (
        <p className="text-sm text-slate-300">No campaigns yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {campaigns.map((c) => (
            <div key={c.id} className="card flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-100">{c.campaign_name}</p>
                <p className="text-xs text-slate-300">{c.channel} · {c.target_count ?? 0} targets</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="label">{c.status}</span>
                {c.status === "active" ? (
                  <button
                    onClick={() => handlePause(c.id)}
                    disabled={busyId === c.id}
                    className="rounded-lg border border-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-900 disabled:opacity-50"
                  >
                    Pause
                  </button>
                ) : (
                  <button
                    onClick={() => handleLaunch(c.id)}
                    disabled={busyId === c.id}
                    className="rounded-lg bg-brand-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50"
                  >
                    {busyId === c.id ? "Launching…" : "Launch"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
