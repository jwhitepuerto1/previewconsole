import type { CampaignsData } from "@/lib/types";

export function CampaignMetrics({ data }: { data: CampaignsData }) {
  return (
    <div className="card">
      <p className="label">{data.campaign_name}</p>
      <div className="mt-4 grid grid-cols-3 gap-4">
        <div>
          <p className="text-2xl font-semibold text-slate-100">{data.open_rate}%</p>
          <p className="text-xs text-slate-500">Open rate</p>
        </div>
        <div>
          <p className="text-2xl font-semibold text-slate-100">{data.reply_rate}%</p>
          <p className="text-xs text-slate-500">Reply rate</p>
        </div>
        <div>
          <p className="text-2xl font-semibold text-slate-100">{data.meetings_scheduled}</p>
          <p className="text-xs text-slate-500">Meetings scheduled</p>
        </div>
      </div>
      <div className="mt-6">
        <p className="label mb-2">Weekly sends</p>
        <div className="flex items-end gap-2">
          {data.weekly_metrics.map((m, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div
                className="w-8 rounded-t bg-brand-accent/60"
                style={{ height: `${Math.max(8, m.sent)}px` }}
                title={`${m.week_ending}: ${m.sent} sent, ${m.opened} opened, ${m.replied} replied`}
              />
              <span className="text-[10px] text-slate-600">W{i + 1}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
