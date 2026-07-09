"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getRole, getToken } from "@/lib/auth";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
    } else if (getRole() === "preview") {
      router.replace("/preview/dashboard");
    } else {
      router.replace("/dashboard");
    }
  }, [router]);

  return null;
}
