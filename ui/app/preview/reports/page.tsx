"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getReport } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { WeeklyReport } from "@/components/WeeklyReport";
import { PreviewCTA } from "@/components/PreviewCTA";
import type { ReportData } from "@/lib/types";

export default function ReportsPage() {
  const router = useRouter();
  const [data, setData] = useState<ReportData | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/preview/register");
      return;
    }
    getReport().then(setData).catch(() => router.push("/preview/register"));
  }, [router]);

  if (!data) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Weekly Report</h1>
      <WeeklyReport data={data} />
      <div>
        <PreviewCTA text="Walk through your deal structure with a raise strategist →" />
      </div>
    </div>
  );
}
