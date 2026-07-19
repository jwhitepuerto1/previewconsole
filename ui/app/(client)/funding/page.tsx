"use client";

import { useEffect, useState } from "react";
import { getRealFundingEvents, getRealFundingSummary } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { RealFundingEvent, RealFundingSummary } from "@/lib/types";

function fmtMoney(n: number | null) {
  if (n == null) return "—";
  return `$${(n / 1_000_000).toFixed(2)}M`;
}

export default function FundingPage() {
  const [summary, setSummary] = useState<RealFundingSummary | null>(null);
  const [events, setEvents] = useState<RealFundingEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view funding.");
      return;
    }
    Promise.all([getRealFundingSummary(), getRealFundingEvents()])
      .then(([s, e]) => { setSummary(s); setEvents(e); })
      .catch(() => setError("Could not load funding data."));
  }, []);

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!summary || !events) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Funding</h1>

      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <p className="label">Raise target</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{fmtMoney(summary.raise_target)}</p>
        </div>
        <div className="card">
          <p className="label">Soft committed</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{fmtMoney(summary.soft_committed)}</p>
        </div>
        <div className="card">
          <p className="label">Hard committed</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{fmtMoney(summary.hard_committed)}</p>
        </div>
        <div className="card">
          <p className="label">Funded</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{fmtMoney(summary.funded)}</p>
        </div>
      </div>

      <div className="card">
        <p className="label mb-1">Percent of target raised</p>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full bg-brand-accent"
            style={{ width: `${Math.min(100, summary.percent_raised * 100)}%` }}
          />
        </div>
        <p className="mt-2 text-sm text-slate-300">{(summary.percent_raised * 100).toFixed(1)}%</p>
      </div>

      <div>
        <p className="label mb-3">Funding events</p>
        {events.length === 0 ? (
          <p className="text-sm text-slate-300">No funding events logged yet.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {events.map((e) => (
              <div key={e.id} className="card flex items-center justify-between">
                <span className="text-sm text-slate-100">{e.event_type?.replace("_", " ")}</span>
                <span className="text-sm font-medium text-slate-100">{fmtMoney(e.amount)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
