import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Capital Context — Raise Preview",
  description: "Preview raise experience — Capital Context IAS.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950">{children}</body>
    </html>
  );
}
