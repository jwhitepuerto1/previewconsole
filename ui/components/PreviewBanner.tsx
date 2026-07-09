"use client";

export function PreviewBanner({ profileName }: { profileName: string }) {
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-6 py-2 text-center text-sm text-amber-300">
      You are viewing a preview raise — <span className="font-semibold">{profileName}</span>. This
      is fictitious data for demonstration only.
    </div>
  );
}
