import type { InvestorRow as InvestorRowType } from "@/lib/types";

export function InvestorRow({ investor }: { investor: InvestorRowType }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <div>
        <p className="text-sm font-medium text-slate-100">{investor.full_name}</p>
        <p className="text-xs text-slate-300">{investor.title} · {investor.company}</p>
      </div>
      <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
        {investor.fit_score}
      </span>
    </div>
  );
}
