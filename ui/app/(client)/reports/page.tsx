"use client";

import { useEffect, useState } from "react";
import { getRealReports } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { RealReport } from "@/lib/types";

export default function ReportsPage() {
  const [reports, setReports] = useState<RealReport[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view reports.");
      return;
    }
    getRealReports().then(setReports).catch(() => setError("Could not load reports."));
  }, []);

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!reports) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Weekly Reports</h1>

      {reports.length === 0 ? (
        <p className="text-sm text-slate-300">No reports generated yet.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {reports.map((r) => (
            <div key={r.id} className="card flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-100">Week ending {r.report_week_ending}</p>
                <span className="label">{r.status}</span>
              </div>
              {r.rep_commentary && <p className="text-sm text-slate-300">{r.rep_commentary}</p>}
              <div className="grid grid-cols-4 gap-3 text-xs text-slate-300">
                <div>
                  <p className="label">Pipeline</p>
                  <p>{String((r.pipeline_summary as { total_in_pipeline?: number })?.total_in_pipeline ?? "—")} in pipeline</p>
                </div>
                <div>
                  <p className="label">Campaigns</p>
                  <p>{String((r.campaign_summary as { emails_sent?: number })?.emails_sent ?? "—")} sent</p>
                </div>
                <div>
                  <p className="label">Meetings</p>
                  <p>{String((r.meeting_summary as { meetings_held?: number })?.meetings_held ?? "—")} held</p>
                </div>
                <div>
                  <p className="label">Funding</p>
                  <p>{String((r.funding_summary as { new_commitments_this_week?: number })?.new_commitments_this_week ?? "—")} new</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
