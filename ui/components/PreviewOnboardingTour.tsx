"use client";

import { useEffect, useState } from "react";

const STEPS = [
  { title: "Welcome to your raise dashboard", body: "This is where you'd track raise health, pipeline, and funding progress in real time." },
  { title: "Investor pipeline", body: "Every qualified investor moves through stages — from prospect to funded — logged and auditable." },
  { title: "Campaign activity", body: "Track email and LinkedIn outreach performance: open rates, replies, and meetings booked." },
  { title: "Data room", body: "Share documents with access-level controls, and see exactly who's viewing what." },
  { title: "Weekly reports", body: "Your assigned Capital Context rep publishes a report every week — no drafts, always current." },
];

const SEEN_KEY = "crm_preview_tour_seen";

export function PreviewOnboardingTour() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!sessionStorage.getItem(SEEN_KEY)) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const finish = () => {
    sessionStorage.setItem(SEEN_KEY, "1");
    setVisible(false);
  };

  const current = STEPS[step];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
      <div className="card max-w-md">
        <p className="label mb-2">Step {step + 1} of {STEPS.length}</p>
        <h3 className="text-lg font-semibold text-slate-100">{current.title}</h3>
        <p className="mt-2 text-sm text-slate-400">{current.body}</p>
        <div className="mt-6 flex justify-between">
          <button onClick={finish} className="text-sm text-slate-500 hover:text-slate-300">
            Skip tour
          </button>
          <button
            onClick={() => (step < STEPS.length - 1 ? setStep(step + 1) : finish())}
            className="rounded-lg bg-brand-accent px-4 py-2 text-sm font-medium text-white hover:bg-brand-accent/90"
          >
            {step < STEPS.length - 1 ? "Next" : "Get started"}
          </button>
        </div>
      </div>
    </div>
  );
}
