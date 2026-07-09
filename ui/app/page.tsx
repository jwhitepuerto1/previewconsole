"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getRole, getToken } from "@/lib/auth";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      // Anonymous visitors are prospects landing on the public marketing
      // URL, not reps/clients who already have credentials — send them to
      // the no-login preview signup, not the rep/client login screen.
      // /login is still directly reachable by URL for reps/clients.
      router.replace("/preview/register");
    } else if (getRole() === "preview") {
      router.replace("/preview/dashboard");
    } else {
      router.replace("/dashboard");
    }
  }, [router]);

  return null;
}
