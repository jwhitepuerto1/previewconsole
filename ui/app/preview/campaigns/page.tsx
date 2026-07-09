"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCampaigns } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { CampaignMetrics } from "@/components/CampaignMetrics";
import type { CampaignsData } from "@/lib/types";

export default function CampaignsPage() {
  const router = useRouter();
  const [data, setData] = useState<CampaignsData | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/preview/register");
      return;
    }
    getCampaigns().then(setData).catch(() => router.push("/preview/register"));
  }, [router]);

  if (!data) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Campaign Activity</h1>
      <CampaignMetrics data={data} />
    </div>
  );
}
