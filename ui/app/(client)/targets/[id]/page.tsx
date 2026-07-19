"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  createActionItem, createLinkedinTouchpoint, createMeeting, createNote, getActionItems,
  getLinkedinTouchpoints, getMeetings, getNotes, getTargets, markTouchpointResponse,
} from "@/lib/api";
import { getActingClientId, needsActingClientId } from "@/lib/auth";
import type { ActionItemRow, LinkedinTouchpointRow, MeetingRow, NoteRow, TargetRow } from "@/lib/types";

export default function InvestorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [target, setTarget] = useState<TargetRow | null>(null);
  const [meetings, setMeetings] = useState<MeetingRow[] | null>(null);
  const [notes, setNotes] = useState<NoteRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  const [meetingType, setMeetingType] = useState("intro_call");
  const [scheduledAt, setScheduledAt] = useState("");
  const [savingMeeting, setSavingMeeting] = useState(false);

  const [expandedMeeting, setExpandedMeeting] = useState<string | null>(null);
  const [actionItems, setActionItems] = useState<ActionItemRow[] | null>(null);
  const [actionText, setActionText] = useState("");

  const [touchpoints, setTouchpoints] = useState<LinkedinTouchpointRow[] | null>(null);
  const [touchpointType, setTouchpointType] = useState("connection_request");
  const [touchpointSummary, setTouchpointSummary] = useState("");
  const [savingTouchpoint, setSavingTouchpoint] = useState(false);
  const [responseTextById, setResponseTextById] = useState<Record<string, string>>({});

  function load() {
    if (needsActingClientId() && !getActingClientId()) {
      setError("Set an acting client above to view this investor.");
      return;
    }
    // No GET /api/targets/{id} in the spec's own route list — the
    // list-then-find is deliberate, not a missing endpoint.
    getTargets().then((all) => setTarget(all.find((t) => t.id === id) ?? null)).catch(() => setError("Could not load investor."));
    getMeetings().then((all) => setMeetings(all.filter((m) => m.investor_target_id === id))).catch(() => setError("Could not load meetings."));
    getNotes(id).then(setNotes).catch(() => setError("Could not load notes."));
    getLinkedinTouchpoints(id).then(setTouchpoints).catch(() => setError("Could not load LinkedIn touchpoints."));
  }

  useEffect(load, [id]);

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    setSavingNote(true);
    try {
      await createNote({ investor_target_id: id, note: noteText });
      setNoteText("");
      getNotes(id).then(setNotes);
    } catch {
      setError("Could not add note.");
    } finally {
      setSavingNote(false);
    }
  }

  async function handleLogMeeting(e: React.FormEvent) {
    e.preventDefault();
    setSavingMeeting(true);
    try {
      await createMeeting({ investor_target_id: id, meeting_type: meetingType, scheduled_at: scheduledAt });
      setScheduledAt("");
      getMeetings().then((all) => setMeetings(all.filter((m) => m.investor_target_id === id)));
    } catch {
      setError("Could not log meeting — this role may not have write:meetings permission.");
    } finally {
      setSavingMeeting(false);
    }
  }

  async function toggleActionItems(meetingId: string) {
    if (expandedMeeting === meetingId) {
      setExpandedMeeting(null);
      setActionItems(null);
      return;
    }
    setExpandedMeeting(meetingId);
    setActionItems(await getActionItems(meetingId));
  }

  async function handleAddActionItem(meetingId: string, e: React.FormEvent) {
    e.preventDefault();
    await createActionItem(meetingId, { action: actionText });
    setActionText("");
    setActionItems(await getActionItems(meetingId));
  }

  async function handleLogTouchpoint(e: React.FormEvent) {
    e.preventDefault();
    setSavingTouchpoint(true);
    try {
      await createLinkedinTouchpoint({ investor_target_id: id, touchpoint_type: touchpointType, content_summary: touchpointSummary || undefined });
      setTouchpointSummary("");
      getLinkedinTouchpoints(id).then(setTouchpoints);
    } catch {
      setError("Could not log touchpoint.");
    } finally {
      setSavingTouchpoint(false);
    }
  }

  async function handleMarkResponse(touchpointId: string) {
    await markTouchpointResponse(touchpointId, responseTextById[touchpointId] ?? "");
    getLinkedinTouchpoints(id).then(setTouchpoints);
  }

  if (error) return <p className="text-sm text-amber-400">{error}</p>;
  if (!target || !meetings || !notes || !touchpoints) return <p className="text-sm text-slate-300">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">{target.full_name}</h1>
        <p className="text-sm text-slate-300">{target.title} · {target.company} · {target.status}</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Notes */}
        <div className="flex flex-col gap-3">
          <p className="label">Notes</p>
          <form onSubmit={handleAddNote} className="card flex flex-col gap-2">
            <textarea
              required value={noteText} onChange={(e) => setNoteText(e.target.value)} rows={2}
              placeholder="Log a note…"
              className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent"
            />
            <button type="submit" disabled={savingNote}
              className="self-start rounded-lg bg-brand-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50">
              {savingNote ? "Saving…" : "Add note"}
            </button>
          </form>
          {notes.length === 0 ? (
            <p className="text-sm text-slate-300">No notes yet.</p>
          ) : (
            notes.map((n) => (
              <div key={n.id} className="card">
                <p className="text-sm text-slate-100">{n.note}</p>
                <p className="mt-1 text-xs text-slate-300">{n.note_type} · {new Date(n.logged_at).toLocaleString()}</p>
              </div>
            ))
          )}
        </div>

        {/* Meetings */}
        <div className="flex flex-col gap-3">
          <p className="label">Meetings</p>
          <form onSubmit={handleLogMeeting} className="card flex flex-wrap items-end gap-3">
            <div>
              <label className="label">Type</label>
              <select value={meetingType} onChange={(e) => setMeetingType(e.target.value)}
                className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent">
                <option value="intro_call">Intro call</option>
                <option value="deep_dive">Deep dive</option>
                <option value="follow_up">Follow up</option>
                <option value="diligence">Diligence</option>
                <option value="closing">Closing</option>
              </select>
            </div>
            <div>
              <label className="label">Scheduled at</label>
              <input required type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)}
                className="mt-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
            </div>
            <button type="submit" disabled={savingMeeting}
              className="rounded-lg bg-brand-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50">
              {savingMeeting ? "Logging…" : "Log meeting"}
            </button>
          </form>

          {meetings.length === 0 ? (
            <p className="text-sm text-slate-300">No meetings logged yet.</p>
          ) : (
            meetings.map((m) => (
              <div key={m.id} className="card">
                <button onClick={() => toggleActionItems(m.id)} className="flex w-full items-center justify-between text-left">
                  <div>
                    <p className="text-sm font-medium text-slate-100">{m.meeting_type?.replace("_", " ")}</p>
                    <p className="text-xs text-slate-300">{m.scheduled_at ? new Date(m.scheduled_at).toLocaleString() : "—"}</p>
                  </div>
                  <span className="label">{m.status}</span>
                </button>

                {expandedMeeting === m.id && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-slate-800 pt-3">
                    <p className="label">Action items</p>
                    {actionItems?.length === 0 && <p className="text-sm text-slate-300">None yet.</p>}
                    {actionItems?.map((a) => (
                      <div key={a.id} className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-1.5">
                        <span className="text-sm text-slate-100">{a.action}</span>
                        <span className="text-xs text-slate-300">{a.completed ? "done" : "open"}</span>
                      </div>
                    ))}
                    <form onSubmit={(e) => handleAddActionItem(m.id, e)} className="flex gap-2">
                      <input value={actionText} onChange={(e) => setActionText(e.target.value)} placeholder="New action item…"
                        className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-brand-accent" />
                      <button type="submit" className="rounded-lg border border-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-900">
                        Add
                      </button>
                    </form>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* LinkedIn */}
        <div className="flex flex-col gap-3">
          <p className="label">LinkedIn</p>
          <form onSubmit={handleLogTouchpoint} className="card flex flex-col gap-2">
            <select value={touchpointType} onChange={(e) => setTouchpointType(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent">
              <option value="connection_request">Connection request</option>
              <option value="message">Message</option>
              <option value="comment">Comment</option>
              <option value="like">Like</option>
              <option value="inmail">InMail</option>
            </select>
            <input value={touchpointSummary} onChange={(e) => setTouchpointSummary(e.target.value)} placeholder="Summary (optional)…"
              className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-accent" />
            <button type="submit" disabled={savingTouchpoint}
              className="self-start rounded-lg bg-brand-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-accent/90 disabled:opacity-50">
              {savingTouchpoint ? "Logging…" : "Log touchpoint"}
            </button>
          </form>

          {touchpoints.length === 0 ? (
            <p className="text-sm text-slate-300">No LinkedIn touchpoints yet.</p>
          ) : (
            touchpoints.map((t) => (
              <div key={t.id} className="card">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-100">{t.touchpoint_type?.replace("_", " ")}</p>
                  <span className="label">{t.sent_at ? new Date(t.sent_at).toLocaleDateString() : "—"}</span>
                </div>
                {t.content_summary && <p className="mt-1 text-sm text-slate-300">{t.content_summary}</p>}

                {t.response_received ? (
                  <p className="mt-2 text-xs text-emerald-400">Responded: {t.response_summary || "—"}</p>
                ) : (
                  <div className="mt-2 flex gap-2">
                    <input
                      value={responseTextById[t.id] ?? ""}
                      onChange={(e) => setResponseTextById((prev) => ({ ...prev, [t.id]: e.target.value }))}
                      placeholder="Response summary…"
                      className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 outline-none focus:border-brand-accent"
                    />
                    <button
                      onClick={() => handleMarkResponse(t.id)}
                      className="rounded-lg border border-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-900"
                    >
                      Mark responded
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
