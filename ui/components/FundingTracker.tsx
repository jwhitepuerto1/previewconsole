import type { FundingData } from "@/lib/types";

function fmtMoney(n: number) {
  return `$${(n / 1_000_000).toFixed(1)}M`;
}

export function FundingTracker({ data }: { data: FundingData }) {
  const { summary } = data;
  const totalCommitted = summary.soft_committed + summary.hard_committed + summary.funded;

  return (
    <div className="card">
      <div className="flex items-baseline justify-between">
        <p className="text-2xl font-semibold text-slate-100">{fmtMoney(totalCommitted)}</p>
        <p className="text-sm text-slate-300">of {fmtMoney(summary.raise_target ?? 0)} target</p>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full bg-brand-accent"
          style={{ width: `${Math.min(100, summary.percent_raised)}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-slate-300">{summary.percent_raised}% raised</p>

      <div className="mt-6 grid grid-cols-2 gap-4">
        <div>
          <p className="text-lg font-semibold text-slate-100">{fmtMoney(summary.soft_committed)}</p>
          <p className="text-xs text-slate-300">Soft committed ({summary.investor_count_soft} investors)</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-100">{fmtMoney(summary.hard_committed)}</p>
          <p className="text-xs text-slate-300">Hard committed</p>
        </div>
      </div>

      <div className="mt-6">
        <p className="label mb-2">Recent events</p>
        <div className="flex flex-col gap-1">
          {data.events.slice(0, 5).map((e, i) => (
            <div key={i} className="flex justify-between text-sm">
              <span className="text-slate-300">{e.event_type.replace("_", " ")}</span>
              <span className="text-slate-200">{fmtMoney(e.amount)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
