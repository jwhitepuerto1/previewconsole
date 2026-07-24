"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  getChecklist, getOnboardingList, getTargets, updateChecklistItem, updateOnboardingStatus,
} from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { ChecklistItemRow, OnboardingRow, TargetRow } from "@/lib/types";

const STATUSES = [
  "initiated", "kyc_pending", "kyc_complete", "docs_sent", "docs_signed",
  "accreditation_pending", "accreditation_complete", "funded",
];

const CHECKLIST_STATUSES = ["pending", "sent", "received", "verified", "waived"];

function fmtMoney(n: number | null) {
  if (n == null) return "—";
  return `$${n.toLocaleString()}`;
}

export default function OnboardingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<OnboardingRow | null>(null);
  const [target, setTarget] = useState<TargetRow | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItemRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  function load() {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view this onboarding record.");
      return;
    }
    // No GET /api/onboarding/{onboarding_id} — only by investor target id or
    // the full list — matches the same list-then-find pattern as targets/[id].
    getOnboardingList()
      .then((all) => {
        const found = all.find((r) => r.id === id) ?? null;
        setRecord(found);
        if (found?.investor_target_id) {
          getTargets().then((targets) => setTarget(targets.find((t) => t.id === found.investor_target_id) ?? null));
        }
      })
      .catch(() => setError("Could not load onboarding record."));
    getChecklist(id).then(setChecklist).catch(() => setError("Could not load checklist."));
  }

  useEffect(load, [id]);

  async function handleStatusChange(status: string) {
    setUpdatingStatus(true);
    try {
      const updated = await updateOnboardingStatus(id, status);
      setRecord(updated);
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleChecklistStatusChange(itemId: string, status: string) {
    await updateChecklistItem(id, itemId, status);
    getChecklist(id).then(setChecklist);
  }

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!record || !checklist) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">{target?.full_name ?? "Onboarding"}</h1>
        <p className="text-sm text-slate-300">{record.structure} · {fmtMoney(record.investment_amount)}</p>
      </div>

      <div className="card flex flex-wrap items-center gap-3">
        <p className="label">Status</p>
        <select
          value={record.status ?? ""}
          disabled={updatingStatus}
          onChange={(e) => handleStatusChange(e.target.value)}
          className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent disabled:opacity-50"
        >
          {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
        {record.kyc_provider && <span className="text-xs text-slate-300">via {record.kyc_provider}</span>}
      </div>

      <div className="grid grid-cols-3 gap-4 text-xs text-slate-300">
        <div className="card">
          <p className="label">KYC completed</p>
          <p className="mt-1 text-slate-100">{record.kyc_completed_at ? new Date(record.kyc_completed_at).toLocaleDateString() : "—"}</p>
        </div>
        <div className="card">
          <p className="label">Accreditation verified</p>
          <p className="mt-1 text-slate-100">{record.accreditation_verified_at ? new Date(record.accreditation_verified_at).toLocaleDateString() : "—"}</p>
        </div>
        <div className="card">
          <p className="label">Docs signed</p>
          <p className="mt-1 text-slate-100">{record.subscription_doc_signed_at ? new Date(record.subscription_doc_signed_at).toLocaleDateString() : "—"}</p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="label">Checklist</p>
        {checklist.map((item) => (
          <div key={item.id} className="card flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-100">{item.item_name}</p>
              <p className="text-xs text-slate-300">{item.item_type}</p>
            </div>
            <select
              value={item.status ?? ""}
              onChange={(e) => handleChecklistStatusChange(item.id, e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-100 outline-none focus:border-brand-accent"
            >
              {CHECKLIST_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}
