"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Calendar, Clock, MapPin, Users, Sparkles, CheckCircle2, AlertCircle, ArrowRight, Video, Plus, X, Check, RefreshCw, Key } from "lucide-react";

export function ScheduleTimeline() {
  const [selectedDate, setSelectedDate] = useState("Today, Jul 5");

  const [events, setEvents] = useState<any[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("API Connection Required");
  const [isRealApiConnected, setIsRealApiConnected] = useState(false);

  useEffect(() => {
    checkGoogleConnection();
  }, []);

  const checkGoogleConnection = async () => {
    try {
      const chiefToken = localStorage.getItem("chief_token");
      if (!chiefToken) return;

      const payload = JSON.parse(atob(chiefToken.split('.')[1]));
      const tenantId = payload.tenant_id;

      // Check with gateway if Calendar scopes are granted
      const res = await fetch(`http://localhost:8002/auth/google/scopes?tenant_id=${tenantId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.granted && data.granted.calendar) {
          setIsRealApiConnected(true);
          setSyncStatus("Connected to Workspace via OAuth");
          fetchRealCalendarData(chiefToken);
        } else {
          setIsRealApiConnected(false);
          setSyncStatus("Calendar API disconnected. Connection required.");
        }
      }
    } catch (e) {
      console.warn("Failed to check Google scopes", e);
    }
  };

  const fetchRealCalendarData = async (token: string) => {
    setIsSyncing(true);
    setSyncStatus("Fetching live events via Gateway...");
    try {
      const response = await fetch("http://localhost:8002/execute/read", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          provider: "google",
          operation: "get_upcoming_events",
          params: { max_results: 8 }
        })
      });

      const data = await response.json();
      if (!response.ok) {
        setSyncStatus(`Connection failed: ${data.detail || "Unknown error"}`);
        setIsRealApiConnected(false);
        return;
      }

      if (data.data && data.data.events) {
        setEvents(data.data.events);
        setSyncStatus("Live Calendar Connected");
      }
    } catch (err: any) {
      setSyncStatus(`Error: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const { getToken, orgId } = useAuth();

  const handleSyncNow = async () => {
    try {
      const token = await getToken();
      if (!token) throw new Error("No token found");
      
      const payload = JSON.parse(atob(token.split('.')[1]));
      // Use Clerk orgId if available, otherwise fallback to parsed tenant_id or user_id
      const tenantId = orgId || payload.tenant_id || payload.sub;
      
      window.location.href = `http://localhost:8002/auth/google/incremental?tenant_id=${tenantId}&service=calendar`;
    } catch (e) {
      console.error(e);
      alert("Please log in first to connect Calendar.");
    }
  };

  return (
    <section className="p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden space-y-6 flex flex-col justify-between">
      {/* Google Calendar Live Integration Bar */}
      <div className="p-3.5 rounded-xl bg-neutral-50 border border-neutral-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-black text-white shadow-2xs shrink-0">
            <Calendar className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-black">Google Calendar Live</span>
              <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-bold uppercase ${
                isRealApiConnected ? "bg-black text-white" : "bg-neutral-200 text-neutral-800 border border-neutral-300"
              }`}>
                {isRealApiConnected ? "LIVE API CONNECTED" : "WORKSPACE SYNCED"}
              </span>
            </div>
            <p className="text-[11px] text-neutral-500 font-mono mt-0.5">{syncStatus}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
          <button
            onClick={handleSyncNow}
            disabled={isSyncing}
            className="px-3 py-1.5 rounded-lg bg-white hover:bg-neutral-100 border border-neutral-300 text-black font-semibold text-xs flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`} />
            <span>{isSyncing ? "Syncing..." : "Sync Calendar"}</span>
          </button>
          <button
            onClick={handleSyncNow}
            className="px-3 py-1.5 rounded-lg bg-black hover:bg-neutral-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
          >
            <Key className="h-3.5 w-3.5" />
            <span>Connect Calendar</span>
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-black tracking-tight">
              Schedule & Executive Calendar
            </h3>
            <span className="px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 text-[10px] font-mono font-bold uppercase">
              {events.length} EVENTS
            </span>
          </div>
          <p className="text-xs text-neutral-500 mt-0.5">
            Calendar Agent dynamically prepares executive briefing notes before every Google Meet sync
          </p>
        </div>
      </div>

      {/* Timeline List */}
      <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-neutral-200">
        {events.length === 0 && (
          <div className="p-10 rounded-xl bg-neutral-50 border border-dashed border-neutral-300 text-center space-y-2 ml-8">
            <Calendar className="h-5 w-5 text-neutral-400 mx-auto" />
            <p className="text-xs font-medium text-neutral-600">No events found</p>
            <p className="text-[11px] text-neutral-400">Click &quot;Connect Calendar&quot; to securely authorize your calendar via OAuth.</p>
          </div>
        )}
        {events.map((evt) => {
          const isDone = evt.status === "Completed";
          const isCurrent = evt.status === "In Progress";
          return (
            <div
              key={evt.id}
              onClick={() => setSelectedEvent(evt)}
              className={`relative pl-8 p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between gap-3 group cursor-pointer ${
                isCurrent
                  ? "bg-white border-black shadow-sm"
                  : isDone
                  ? "bg-neutral-50/60 border-neutral-200 opacity-70"
                  : "bg-white hover:bg-neutral-50 border-neutral-200 hover:border-neutral-300"
              }`}
            >
              {/* Timeline dot */}
              <div
                className={`absolute left-2 top-5 h-3.5 w-3.5 rounded-full border-2 transition-transform group-hover:scale-110 ${
                  isCurrent
                    ? "bg-black border-black animate-pulse"
                    : isDone
                    ? "bg-neutral-300 border-neutral-400"
                    : "bg-white border-neutral-400"
                }`}
              />

              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-black">{evt.time}</span>
                    <span className="text-[10px] font-mono text-neutral-500">({evt.duration})</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-700 border border-neutral-200 font-semibold">
                      {evt.type}
                    </span>
                  </div>
                  <h4 className={`text-xs font-bold mt-1 group-hover:underline transition-all ${isCurrent ? "text-black font-extrabold" : "text-neutral-800"}`}>
                    {evt.title}
                  </h4>
                </div>

                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold shrink-0 ${
                    isCurrent
                      ? "bg-black text-white"
                      : isDone
                      ? "bg-neutral-200 text-neutral-600"
                      : "bg-neutral-100 text-neutral-700 border border-neutral-200"
                  }`}
                >
                  {evt.status}
                </span>
              </div>

              {/* AI Briefing Preview */}
              <div className="p-2.5 rounded-lg bg-neutral-100/70 border border-neutral-200 text-xs text-neutral-700 flex items-start gap-2">
                <Sparkles className="h-3.5 w-3.5 text-neutral-600 shrink-0 mt-0.5" />
                <p className="font-normal leading-relaxed text-[11px] line-clamp-2">{evt.briefing}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Event Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-neutral-200 shadow-2xl p-6 relative overflow-hidden animate-in zoom-in-95 duration-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-200">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-black" />
                <h4 className="text-sm font-bold text-black">Executive Event Sync</h4>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="p-1 rounded-lg text-neutral-400 hover:text-black hover:bg-neutral-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-semibold">Event Title</span>
                <h3 className="text-base font-bold text-black mt-0.5">{selectedEvent.title}</h3>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-neutral-50 border border-neutral-200 text-xs font-mono">
                <div>
                  <span className="text-neutral-400 uppercase text-[10px] block">Time & Duration</span>
                  <span className="text-black font-bold mt-0.5 block">{selectedEvent.time} ({selectedEvent.duration})</span>
                </div>
                <div>
                  <span className="text-neutral-400 uppercase text-[10px] block">Location / Platform</span>
                  <span className="text-black font-bold mt-0.5 block">{selectedEvent.location}</span>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-semibold">Attendees ({selectedEvent.attendees.length})</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {selectedEvent.attendees.map((att: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 rounded-lg bg-neutral-100 border border-neutral-200 text-black text-xs font-medium">
                      {att}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-semibold">AI Executive Briefing Memo</span>
                <div className="p-3.5 rounded-xl bg-neutral-50 border border-neutral-200 text-xs text-neutral-800 leading-relaxed font-normal mt-1 flex items-start gap-2.5">
                  <Sparkles className="h-4 w-4 text-black shrink-0 mt-0.5" />
                  <p>{selectedEvent.briefing}</p>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-neutral-200 flex items-center justify-end gap-2.5">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium transition-colors cursor-pointer border border-neutral-300"
              >
                Close
              </button>
              <button
                onClick={() => {
                  alert(`Joining ${selectedEvent.title} via ${selectedEvent.location} as charanchandra1006@gmail.com...`);
                  setSelectedEvent(null);
                }}
                className="px-5 py-2 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Video className="h-3.5 w-3.5" />
                <span>Join Google Meet Now</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
