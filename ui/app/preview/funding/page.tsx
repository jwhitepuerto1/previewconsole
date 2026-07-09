"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getFunding } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { FundingTracker } from "@/components/FundingTracker";
import type { FundingData } from "@/lib/types";

export default function FundingPage() {
  const router = useRouter();
  const [data, setData] = useState<FundingData | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/preview/register");
      return;
    }
    getFunding().then(setData).catch(() => router.push("/preview/register"));
  }, [router]);

  if (!data) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Funding</h1>
      <FundingTracker data={data} />
    </div>
  );
}
