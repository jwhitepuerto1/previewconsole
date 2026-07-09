"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDataRoom } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { DataRoomPanel } from "@/components/DataRoomPanel";
import { PreviewCTA } from "@/components/PreviewCTA";
import type { DataRoomData } from "@/lib/types";

export default function DataRoomPage() {
  const router = useRouter();
  const [data, setData] = useState<DataRoomData | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/preview/register");
      return;
    }
    getDataRoom().then(setData).catch(() => router.push("/preview/register"));
  }, [router]);

  if (!data) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Data Room</h1>
      <DataRoomPanel data={data} />
      <div>
        <PreviewCTA text="Ready to map this to your raise? →" />
      </div>
    </div>
  );
}
