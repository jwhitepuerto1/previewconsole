"use client";

import { useState } from "react";
import { getActingClientId, needsActingClientId, setActingClientId } from "@/lib/auth";

export function ClientSwitcher({ onSet }: { onSet: () => void }) {
  const [value, setValue] = useState(getActingClientId() ?? "");

  if (!needsActingClientId()) return null;

  return (
    <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900 px-6 py-2">
      <span className="text-xs text-slate-500">Acting as client:</span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="client UUID"
        className="w-96 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200 outline-none focus:border-brand-accent"
      />
      <button
        onClick={() => { setActingClientId(value); onSet(); }}
        className="rounded bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700"
      >
        Set
      </button>
    </div>
  );
}
