"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDashboard } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { PreviewCTA } from "@/components/PreviewCTA";
import type { DashboardData } from "@/lib/types";

function fmtMoney(n: number | null) {
  if (n == null) return "—";
  return `$${(n / 1_000_000).toFixed(1)}M`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/preview/register");
      return;
    }
    getDashboard().then(setData).catch(() => router.push("/preview/register"));
  }, [router]);

  if (!data) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">{data.raise_name}</h1>
        <p className="text-sm text-slate-500">Day {data.days_active} of active raise</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <p className="label">Raise target</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{fmtMoney(data.raise_target)}</p>
        </div>
        <div className="card">
          <p className="label">Investors in pipeline</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{data.investor_count}</p>
        </div>
        <div className="card">
          <p className="label">Percent raised</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{data.funding.percent_raised}%</p>
        </div>
        <div className="card">
          <p className="label">Soft + hard committed</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">
            {fmtMoney(data.funding.soft_committed + data.funding.hard_committed)}
          </p>
        </div>
      </div>

      <div className="card">
        <p className="label mb-3">Pipeline by stage</p>
        <div className="flex flex-wrap gap-3">
          {Object.entries(data.pipeline_by_stage).map(([stage, count]) => (
            <div key={stage} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
              <p className="text-sm text-slate-200">{count}</p>
              <p className="text-xs text-slate-500">{stage.replace("_", " ")}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <PreviewCTA text="Ready to map this to your raise? →" />
      </div>
    </div>
  );
}
