"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getPipeline } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { PipelineBoard } from "@/components/PipelineBoard";
import { PreviewCTA } from "@/components/PreviewCTA";
import type { PipelineData } from "@/lib/types";

export default function PipelinePage() {
  const router = useRouter();
  const [data, setData] = useState<PipelineData | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/preview/register");
      return;
    }
    getPipeline().then(setData).catch(() => router.push("/preview/register"));
  }, [router]);

  if (!data) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Investor Pipeline</h1>
      <PipelineBoard investors={data.investors} />
      <div>
        <PreviewCTA text="Walk through your deal structure with a raise strategist →" />
      </div>
    </div>
  );
}
