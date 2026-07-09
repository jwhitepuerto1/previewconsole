"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/api";
import { storeSession } from "@/lib/auth";

const DEAL_TYPES = [
  { value: "cre_syndication", label: "CRE Syndication" },
  { value: "private_credit", label: "Private Credit" },
  { value: "real_estate_fund", label: "Real Estate Fund" },
  { value: "other", label: "Other" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [dealType, setDealType] = useState("cre_syndication");
  const [raiseTarget, setRaiseTarget] = useState("20000000");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await register(name, email, dealType, Number(raiseTarget));
      storeSession(res.token, res.profile_name);
      router.push("/preview/dashboard");
    } catch {
      setError("Something went wrong — please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <form onSubmit={handleSubmit} className="card w-full max-w-md">
        <h1 className="text-xl font-semibold text-slate-100">See your raise, live</h1>
        <p className="mt-1 text-sm text-slate-300">
          A quick preview of the Capital Context raise operating environment — built on a
          fictitious deal matched to your profile.
        </p>

        <div className="mt-6 flex flex-col gap-4">
          <div>
            <label className="label">Name</label>
            <input
              required type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent"
            />
          </div>
          <div>
            <label className="label">Email</label>
            <input
              required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent"
            />
          </div>
          <div>
            <label className="label">Deal type</label>
            <select
              value={dealType} onChange={(e) => setDealType(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent"
            >
              {DEAL_TYPES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Raise target ($)</label>
            <input
              required type="number" value={raiseTarget} onChange={(e) => setRaiseTarget(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent"
            />
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

        <button
          type="submit" disabled={loading}
          className="mt-6 w-full rounded-lg bg-brand-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-accent/90 disabled:opacity-50"
        >
          {loading ? "Loading preview…" : "View my raise preview"}
        </button>
      </form>
    </div>
  );
}
