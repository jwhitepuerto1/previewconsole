"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getOnboardingList, getTargets, initiateOnboarding } from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { OnboardingRow, TargetRow } from "@/lib/types";

function fmtMoney(n: number | null) {
  if (n == null) return "—";
  return `$${n.toLocaleString()}`;
}

export default function OnboardingPage() {
  const [records, setRecords] = useState<OnboardingRow[] | null>(null);
  const [targets, setTargets] = useState<TargetRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [targetId, setTargetId] = useState("");
  const [amount, setAmount] = useState("");
  const [structure, setStructure] = useState("equity");
  const [submitting, setSubmitting] = useState(false);

  function load() {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view onboarding.");
      return;
    }
    getOnboardingList().then(setRecords).catch(() => setError("Could not load onboarding records."));
    getTargets().then(setTargets).catch(() => setError("Could not load investors."));
  }

  useEffect(load, []);

  async function handleInitiate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await initiateOnboarding({
        investor_target_id: targetId,
        investment_amount: amount ? Number(amount) : undefined,
        structure,
      });
      setTargetId("");
      setAmount("");
      getOnboardingList().then(setRecords);
    } catch {
      setError("Could not initiate onboarding — this role may not have write:onboarding permission.");
    } finally {
      setSubmitting(false);
    }
  }

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!records || !targets) return <p className="text-sm text-slate-300">Loading…</p>;

  const nameById = new Map(targets.map((t) => [t.id, t.full_name]));
  // Only investors without an existing onboarding record are eligible to start one.
  const onboardedIds = new Set(records.map((r) => r.investor_target_id));
  const eligibleTargets = targets.filter((t) => !onboardedIds.has(t.id));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-slate-100">Onboarding</h1>

      <form onSubmit={handleInitiate} className="card flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Investor</label>
          <select required value={targetId} onChange={(e) => setTargetId(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent">
            <option value="" disabled>Select investor…</option>
            {eligibleTargets.map((t) => (
              <option key={t.id} value={t.id}>{t.full_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Investment amount</label>
          <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="250000"
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
        </div>
        <div>
          <label className="label">Structure</label>
          <select value={structure} onChange={(e) => setStructure(e.target.value)}
            className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent">
            <option value="equity">Equity</option>
            <option value="debt">Debt</option>
            <option value="preferred">Preferred</option>
            <option value="other">Other</option>
          </select>
        </div>
        <button type="submit" disabled={submitting}
          className="rounded-lg bg-brand-accent px-4 py-2 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50">
          {submitting ? "Initiating…" : "Initiate onboarding"}
        </button>
      </form>

      {records.length === 0 ? (
        <p className="text-sm text-slate-300">No investors in onboarding yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {records.map((r) => (
            <Link key={r.id} href={`/onboarding/${r.id}`}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 hover:border-brand-accent">
              <div>
                <p className="text-sm font-medium text-slate-100">{nameById.get(r.investor_target_id ?? "") ?? "Unknown investor"}</p>
                <p className="text-xs text-slate-300">{r.structure} · {fmtMoney(r.investment_amount)}</p>
              </div>
              <span className="label">{r.status}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
