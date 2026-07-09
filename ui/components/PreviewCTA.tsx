"use client";

import { track } from "@/lib/api";

export function PreviewCTA({ text }: { text: string }) {
  return (
    <button
      onClick={() => track("cta_click", text)}
      className="rounded-lg border border-brand-accent/40 bg-brand-accent/10 px-4 py-2 text-sm font-medium text-brand-accent transition hover:bg-brand-accent/20"
    >
      {text}
    </button>
  );
}
