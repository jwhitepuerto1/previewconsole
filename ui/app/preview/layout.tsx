"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { PreviewBanner } from "@/components/PreviewBanner";
import { PreviewOnboardingTour } from "@/components/PreviewOnboardingTour";
import { getProfileName, getToken } from "@/lib/auth";
import { track } from "@/lib/api";

export default function PreviewLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [profileName, setProfileName] = useState<string | null>(null);
  const isRegisterPage = pathname === "/preview/register";

  useEffect(() => {
    setProfileName(getProfileName());
    if (!isRegisterPage && getToken()) {
      track("page_visit", pathname);
    }
  }, [pathname, isRegisterPage]);

  return (
    <div className="min-h-screen">
      {!isRegisterPage && profileName && <PreviewBanner profileName={profileName} />}
      {!isRegisterPage && <Nav />}
      <main className="mx-auto max-w-screen-2xl px-6 py-8">{children}</main>
      {!isRegisterPage && <PreviewOnboardingTour />}
    </div>
  );
}
