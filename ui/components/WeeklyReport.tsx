import type { ReportData } from "@/lib/types";

export function WeeklyReport({ data }: { data: ReportData }) {
  return (
    <div className="card">
      <p className="label">Week ending {data.report_week_ending}</p>

      <div className="mt-4">
        <p className="text-sm font-semibold text-slate-200">Key activities</p>
        <p className="mt-1 text-sm text-slate-300">{data.key_activities}</p>
      </div>

      <div className="mt-4">
        <p className="text-sm font-semibold text-slate-200">Next week priorities</p>
        <p className="mt-1 text-sm text-slate-300">{data.next_week_priorities}</p>
      </div>

      <div className="mt-4 rounded-lg border border-brand-accent/30 bg-brand-accent/5 p-3">
        <p className="text-sm font-semibold text-brand-accent">Rep commentary</p>
        <p className="mt-1 text-sm text-slate-300">{data.rep_commentary}</p>
      </div>
    </div>
  );
}
