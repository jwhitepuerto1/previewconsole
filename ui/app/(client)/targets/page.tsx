"use client";

import { useEffect, useState } from "react";
import { createTarget, getTargets } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { TargetRow } from "@/lib/types";

export default function TargetsPage() {
  const [targets, setTargets] = useState<TargetRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function load() {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view targets.");
      return;
    }
    getTargets().then(setTargets).catch(() => setError("Could not load targets."));
  }

  useEffect(load, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createTarget({ full_name: fullName, company, title });
      setFullName(""); setCompany(""); setTitle("");
      load();
    } catch {
      setError("Could not add investor — this role may not have write:targets permission.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Investor Targets</h1>

      <form onSubmit={handleAdd} className="card flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Full name</label>
          <input required value={fullName} onChange={(e) => setFullName(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
        </div>
        <div>
          <label className="label">Company</label>
          <input value={company} onChange={(e) => setCompany(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
        </div>
        <div>
          <label className="label">Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
        </div>
        <button type="submit" disabled={submitting}
          className="rounded-lg bg-brand-accent px-4 py-2 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50">
          {submitting ? "Adding…" : "Add investor"}
        </button>
      </form>

      {error && <p className="text-sm text-amber-400">{error}</p>}

      {targets && (
        <div className="flex flex-col gap-2">
          {targets.length === 0 ? (
            <p className="text-sm text-slate-500">No targets yet.</p>
          ) : (
            targets.map((t) => (
              <div key={t.id} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
                <div>
                  <p className="text-sm font-medium text-slate-100">{t.full_name}</p>
                  <p className="text-xs text-slate-500">{t.title} · {t.company}</p>
                </div>
                <span className="text-xs text-slate-500">{t.status}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
