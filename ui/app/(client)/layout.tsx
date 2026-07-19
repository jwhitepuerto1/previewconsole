"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { ClientSwitcher } from "@/components/ClientSwitcher";
import { AlertBell } from "@/components/AlertBell";
import { getToken } from "@/lib/auth";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [, forceRerender] = useState(0);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) return null;

  return (
    <div className="min-h-screen">
      <Nav variant="client" right={<AlertBell />} />
      <ClientSwitcher onSet={() => forceRerender((n) => n + 1)} />
      <main className="mx-auto max-w-screen-2xl px-6 py-8">{children}</main>
    </div>
  );
}
