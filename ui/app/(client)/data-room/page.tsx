"use client";

import { useEffect, useState } from "react";
import { getRealDataRoom } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { RealDocument } from "@/lib/types";

function fmtSize(bytes: number | null) {
  if (bytes == null) return "—";
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export default function DataRoomPage() {
  const [docs, setDocs] = useState<RealDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view the data room.");
      return;
    }
    getRealDataRoom().then(setDocs).catch(() => setError("Could not load data room."));
  }, []);

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!docs) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Data Room</h1>
      <p className="text-sm text-slate-300">
        Read-only investors see only documents marked <span className="text-slate-100">public</span> — everything else
        requires a client team/rep role or an explicit grant.
      </p>

      {docs.length === 0 ? (
        <p className="text-sm text-slate-300">No documents uploaded yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {docs.map((d) => (
            <div key={d.id} className="card flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-100">{d.document_name}</p>
                <p className="text-xs text-slate-300">{d.document_type} · {fmtSize(d.file_size_bytes)} · v{d.version}</p>
              </div>
              <span className="label">{d.access_level}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
