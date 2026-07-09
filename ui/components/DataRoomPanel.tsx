import type { DataRoomData } from "@/lib/types";

const ACCESS_COLORS: Record<string, string> = {
  public: "bg-emerald-500/20 text-emerald-300",
  qualified: "bg-blue-500/20 text-blue-300",
  committed: "bg-purple-500/20 text-purple-300",
  restricted: "bg-red-500/20 text-red-300",
};

export function DataRoomPanel({ data }: { data: DataRoomData }) {
  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <p className="label">Documents</p>
        <p className="text-sm text-slate-400">{data.views_this_week} views this week</p>
      </div>
      <div className="flex flex-col gap-2">
        {data.documents.map((doc) => (
          <div key={doc.id} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
            <span className="text-sm text-slate-200">{doc.name}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs ${ACCESS_COLORS[doc.access_level] ?? "bg-slate-800 text-slate-300"}`}>
              {doc.access_level}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
