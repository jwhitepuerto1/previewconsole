import type { InvestorRow as InvestorRowType } from "@/lib/types";
import { InvestorRow } from "./InvestorRow";

export const STAGE_LABELS: Record<string, string> = {
  prospect: "Prospect",
  qualified: "Qualified",
  engaged: "Engaged",
  meeting_scheduled: "Meeting Scheduled",
  meeting_completed: "Meeting Completed",
  soft_committed: "Soft Committed",
  committed: "Committed",
  onboarding: "Onboarding",
  funded: "Funded",
  declined: "Declined",
  on_hold: "On Hold",
};

interface PipelineBoardProps {
  investors: InvestorRowType[];
  onMoveStage?: (investorId: string, newStage: string) => void;
}

export function PipelineBoard({ investors, onMoveStage }: PipelineBoardProps) {
  const byStage = new Map<string, InvestorRowType[]>();
  for (const inv of investors) {
    const list = byStage.get(inv.stage) ?? [];
    list.push(inv);
    byStage.set(inv.stage, list);
  }

  const stages = [...byStage.keys()].sort(
    (a, b) => (byStage.get(b)?.length ?? 0) - (byStage.get(a)?.length ?? 0),
  );

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {stages.map((stage) => (
        <div key={stage} className="w-72 flex-shrink-0">
          <div className="mb-2 flex items-center justify-between">
            <p className="label">{STAGE_LABELS[stage] ?? stage}</p>
            <span className="text-xs text-slate-300">{byStage.get(stage)?.length}</span>
          </div>
          <div className="flex flex-col gap-2">
            {byStage.get(stage)?.map((inv) => (
              <div key={inv.id}>
                <InvestorRow investor={inv} />
                {onMoveStage && (
                  <select
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) onMoveStage(inv.id, e.target.value);
                      e.target.value = "";
                    }}
                    className="mt-1 w-full rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-300 outline-none focus:border-brand-accent"
                  >
                    <option value="" disabled>Move to…</option>
                    {Object.entries(STAGE_LABELS)
                      .filter(([key]) => key !== stage)
                      .map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                  </select>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
