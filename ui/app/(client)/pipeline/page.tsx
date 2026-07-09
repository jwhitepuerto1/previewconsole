"use client";

import { useEffect, useState } from "react";
import { getRealPipeline, patchPipelineStage } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import { PipelineBoard } from "@/components/PipelineBoard";
import type { PipelineData } from "@/lib/types";

export default function RealPipelinePage() {
  const [data, setData] = useState<PipelineData | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view a pipeline.");
      return;
    }
    getRealPipeline().then(setData).catch(() => setError("Could not load pipeline."));
  }

  useEffect(load, []);

  async function handleMove(investorId: string, newStage: string) {
    await patchPipelineStage(investorId, newStage);
    load();
  }

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!data) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Investor Pipeline</h1>
      {data.investors.length === 0 ? (
        <p className="text-sm text-slate-300">No investors yet — add one from the Targets page.</p>
      ) : (
        <PipelineBoard investors={data.investors} onMoveStage={handleMove} />
      )}
    </div>
  );
}
