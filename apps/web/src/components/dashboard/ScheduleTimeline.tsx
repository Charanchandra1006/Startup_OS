"use client";

import React, { useState, useEffect } from "react";
import { Calendar, Clock, MapPin, Users, Sparkles, CheckCircle2, AlertCircle, ArrowRight, Video, Plus, X, Check, RefreshCw, Key } from "lucide-react";

export function ScheduleTimeline() {
  const [selectedDate, setSelectedDate] = useState("Today, Jul 5");

  const defaultEvents = [
    {
      id: "evt-1",
      time: "09:00 AM",
      title: "Executive Standup & Autonomous Agent Sync",
      type: "Internal",
      duration: "30 min",
      attendees: ["Charan Chandra", "AI Orchestrator", "Dept Agents"],
      location: "Google Meet / Voice Command",
      status: "Completed",
      briefing: "AI CFO reported 12% revenue growth and 40.2 mo runway. Marketing Agent deployed Q3 growth campaigns.",
    },
    {
      id: "evt-2",
      time: "11:30 AM",
      title: "Series A Term Sheet Deep Dive",
      type: "Investor",
      duration: "45 min",
      attendees: ["Charan Chandra", "Marcus Vance (Alpha Ventures)", "AI Legal Agent"],
      location: "Google Meet Video Call",
      status: "In Progress",
      briefing: "Negotiating $65M pre-money valuation terms and board governance clauses. AI Legal has prepared redline fallbacks.",
    },
    {
      id: "evt-3",
      time: "02:00 PM",
      title: "Enterprise Onboarding Kickoff — CloudScale Inc.",
      type: "Client",
      duration: "60 min",
      attendees: ["Sarah Jenkins (VP Eng)", "Charan Chandra", "AI Ops Agent"],
      location: "Google Meet",
      status: "Upcoming",
      briefing: "Finalizing 500-seat API provisioning and dedicated Slack connect channel. Contract value: $180,000 ARR.",
    },
    {
      id: "evt-4",
      time: "04:30 PM",
      title: "Google Workspace & GCP Infrastructure Review",
      type: "Engineering",
      duration: "45 min",
      attendees: ["Charan Chandra", "David K. (Board)", "AI Ops Agent"],
      location: "Google Meet / Hybrid",
      status: "Upcoming",
      briefing: "Reviewing compute budget and API gateway allocation for charanchandra1006@gmail.com.",
    },
  ];

  const [events, setEvents] = useState<any[]>(defaultEvents);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showGoogleModal, setShowGoogleModal] = useState(false);
  const [googleToken, setGoogleToken] = useState("");
  const [syncStatus, setSyncStatus] = useState("Connected to Workspace (charanchandra1006@gmail.com)");
  const [isRealApiConnected, setIsRealApiConnected] = useState(false);

  useEffect(() => {
    const savedToken = localStorage.getItem("google_oauth_token");
    if (savedToken) {
      setGoogleToken(savedToken);
      setIsRealApiConnected(true);
      fetchRealCalendarData(savedToken);
    }
  }, []);

  const fetchRealCalendarData = async (token: string) => {
    setIsSyncing(true);
    setSyncStatus("Fetching live events from Google Calendar API...");
    try {
      // Use server-side proxy to avoid CORS restrictions
      const response = await fetch("/api/google/calendar?maxResults=8", {
        headers: {
          Authorization: `Bearer ${token.trim()}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data?.detail?.error?.message || data?.error || "Token may be expired or missing required scopes.";
        setSyncStatus(`Connection failed: ${detail}`);
        setIsRealApiConnected(false);
        setIsSyncing(false);
        return;
      }

      if (data.events && data.events.length > 0) {
        setEvents(data.events);
        setIsRealApiConnected(true);
        setSyncStatus(`Live Google Calendar API Active — ${data.events.length} events loaded (charanchandra1006@gmail.com)`);
      } else {
        setSyncStatus("Calendar API connected. No upcoming events found.");
        setIsRealApiConnected(true);
      }
    } catch (err: any) {
      console.error("Calendar proxy error:", err);
      setIsRealApiConnected(false);
      setSyncStatus(`Error: ${err.message || "Could not reach Calendar proxy. Check console."}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSyncNow = () => {
    const token = localStorage.getItem("google_oauth_token") || googleToken;
    if (token && token.trim().length > 10) {
      fetchRealCalendarData(token.trim());
    } else {
      setSyncStatus("No OAuth token saved. Click 'API Settings' to connect your Calendar.");
      setShowGoogleModal(true);
    }
  };

  const handleSaveToken = (e: React.FormEvent) => {
    e.preventDefault();
    if (googleToken.trim()) {
      localStorage.setItem("google_oauth_token", googleToken.trim());
      setIsRealApiConnected(true);
      setShowGoogleModal(false);
      fetchRealCalendarData(googleToken.trim());
    } else {
      localStorage.removeItem("google_oauth_token");
      setIsRealApiConnected(false);
      setShowGoogleModal(false);
      setEvents(defaultEvents);
      setSyncStatus("Connected to Workspace (charanchandra1006@gmail.com)");
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
            onClick={() => setShowGoogleModal(true)}
            className="px-3 py-1.5 rounded-lg bg-black hover:bg-neutral-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
          >
            <Key className="h-3.5 w-3.5" />
            <span>API Settings</span>
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

      {/* Google Calendar API Settings Modal */}
      {showGoogleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-neutral-200 shadow-2xl p-6 relative overflow-hidden animate-in zoom-in-95 duration-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-200">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-black" />
                <h4 className="text-sm font-bold text-black">Google Calendar API Connector</h4>
              </div>
              <button
                onClick={() => setShowGoogleModal(false)}
                className="p-1 rounded-lg text-neutral-400 hover:text-black hover:bg-neutral-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSaveToken} className="space-y-4">
              <div className="p-3.5 rounded-xl bg-neutral-50 border border-neutral-200 text-xs space-y-1">
                <span className="font-bold text-black block">Connected Account: charanchandra1006@gmail.com</span>
                <p className="text-neutral-600 leading-relaxed">
                  You are currently synced to your Google Workspace calendar schedule. To pull real-time meetings directly from Google Calendar servers, paste your OAuth Bearer Token below.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-black mb-1 font-mono">
                  Google OAuth Access Token (e.g. ya29.a0...)
                </label>
                <input
                  type="password"
                  value={googleToken}
                  onChange={(e) => setGoogleToken(e.target.value)}
                  placeholder="Paste Google OAuth Token or leave blank for default sync..."
                  className="w-full p-3 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black font-mono focus:outline-none focus:border-black transition-colors"
                />
                <p className="text-[10px] text-neutral-400 mt-1 font-mono">
                  Tokens can be generated instantly from Google OAuth Playground with scope: https://www.googleapis.com/auth/calendar.readonly
                </p>
              </div>

              <div className="pt-4 border-t border-neutral-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setGoogleToken("");
                    localStorage.removeItem("google_oauth_token");
                    setIsRealApiConnected(false);
                    setEvents(defaultEvents);
                    setShowGoogleModal(false);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium transition-colors cursor-pointer border border-neutral-300"
                >
                  Reset to Default Sync
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Save & Connect API</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
