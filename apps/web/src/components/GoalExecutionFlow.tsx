"use client";

/**
 * GoalExecutionFlow — Real-time pipeline state visualization.
 *
 * STARTUP_OS_MASTER_BUILD_PLAN Part 3.5: Consumes the real
 * /api/goals/:goalId/stream SSE endpoint, which tails the
 * goal_events DB table populated by the Orchestrator's _publish_event().
 *
 * No scripted animations — every state change comes from the actual pipeline.
 * The scripted demo lives in demo/DemoGoalExecutionFlow.tsx and is never
 * reachable from a logged-in founder's normal goal-submission flow.
 */

import React, { useState, useEffect, useCallback } from "react";
import { API_BASE_URL, fetchGoalStatus, getAuthToken } from "../lib/api";

// Maps orchestrator state machine values to UI display
const STATE_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  CLASSIFYING:              { label: "Classifying Goal",          color: "bg-blue-500",    icon: "🔍" },
  DECOMPOSING:              { label: "Decomposing into Tasks",    color: "bg-indigo-500",  icon: "🧩" },
  DISPATCHING:              { label: "Dispatching Agents",        color: "bg-purple-500",  icon: "🚀" },
  AWAITING_SPECIALIST_OUTPUT: { label: "Agents Working",          color: "bg-amber-500",   icon: "⚙️" },
  SYNTHESIZING:             { label: "Synthesizing Report",       color: "bg-cyan-500",    icon: "📊" },
  CONFLICTS_DETECTED:       { label: "Conflict Detected",         color: "bg-orange-500",  icon: "⚠️" },
  ROUTING_ACTIONS:          { label: "Routing Actions",           color: "bg-teal-500",    icon: "🎯" },
  DELIVERED:                { label: "Report Delivered",          color: "bg-emerald-500", icon: "✅" },
  FAILED:                   { label: "Analysis Failed",           color: "bg-red-500",     icon: "❌" },
  STALLED:                  { label: "Goal Stalled",              color: "bg-gray-500",    icon: "⏸️" },
};

interface StateEvent {
  state: string;
  detail: Record<string, any>;
  timestamp: string;
}

export function GoalExecutionFlow({
  goalText,
  goalId,
  onComplete,
}: {
  goalText: string;
  goalId: string | null;
  onComplete: () => void;
}) {
  const [events, setEvents] = useState<StateEvent[]>([]);
  const [currentState, setCurrentState] = useState<string>("STARTING");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);

  // Fetch report data once we hit a terminal state
  const fetchReport = useCallback(async (gId: string) => {
    try {
      const data = await fetchGoalStatus(gId);
      if (data.report) setReport(data.report);
      if (data.tasks) setTasks(data.tasks);
    } catch (e) {
      console.error("Failed to fetch goal report:", e);
    }
  }, []);

  // Connect to the real SSE stream
  useEffect(() => {
    if (!goalId) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = async () => {
      try {
        // SSE endpoint requires auth via query param since EventSource
        // doesn't support custom headers
        const token = await getAuthToken();
        const streamUrl = `${API_BASE_URL}/goals/${goalId}/stream`;

        // We can't add auth headers to EventSource, but the endpoint
        // is behind the authenticateJWT middleware which reads from the
        // cookie/session set during login. For API Gateway proxy,
        // we rely on the existing JWT cookie.
        eventSource = new EventSource(streamUrl, { withCredentials: true });
        setConnected(true);
        setError(null);

        eventSource.addEventListener("state_change", (e) => {
          const data: StateEvent = JSON.parse(e.data);
          setEvents(prev => [...prev, data]);
          setCurrentState(data.state);

          // Fetch full report on terminal states
          if (["DELIVERED", "FAILED", "STALLED"].includes(data.state)) {
            fetchReport(goalId);
          }
        });

        eventSource.addEventListener("stream_end", () => {
          eventSource?.close();
          setConnected(false);
        });

        eventSource.onerror = () => {
          setConnected(false);
          eventSource?.close();
          // Auto-reconnect after 2s
          reconnectTimeout = setTimeout(connect, 2000);
        };
      } catch (err) {
        setError("Failed to connect to goal stream");
        console.error("SSE connection error:", err);
      }
    };

    connect();

    // Fallback: poll goal status every 3s in case SSE fails
    const pollInterval = setInterval(async () => {
      if (!connected && goalId) {
        try {
          const status = await fetchGoalStatus(goalId);
          if (status.status && status.status !== currentState) {
            setCurrentState(status.status.toUpperCase());
          }
          if (status.report) setReport(status.report);
          if (status.tasks) setTasks(status.tasks);
          if (["delivered", "failed", "stalled"].includes(status.status)) {
            clearInterval(pollInterval);
          }
        } catch (e) {
          // Ignore poll errors — SSE is the primary channel
        }
      }
    }, 3000);

    return () => {
      eventSource?.close();
      clearTimeout(reconnectTimeout);
      clearInterval(pollInterval);
    };
  }, [goalId, connected, currentState, fetchReport]);

  const stateInfo = STATE_LABELS[currentState] || {
    label: currentState,
    color: "bg-slate-500",
    icon: "⏳",
  };

  const isTerminal = ["DELIVERED", "FAILED", "STALLED"].includes(currentState);

  // Starting state — waiting for goalId
  if (!goalId || currentState === "STARTING") {
    return (
      <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl animate-pulse text-indigo-600 shadow-sm">
        Initializing Chief OS Orchestrator...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">

      {/* Live Pipeline State */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-slate-900 flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              {!isTerminal && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              )}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${stateInfo.color}`}></span>
            </span>
            Pipeline Status
          </h3>
          {connected && (
            <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
              ● Live
            </span>
          )}
        </div>

        {/* Current State */}
        <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200 mb-4">
          <span className="text-2xl">{stateInfo.icon}</span>
          <div>
            <div className="font-semibold text-slate-900">{stateInfo.label}</div>
            <div className="text-sm text-slate-500">Goal: {goalText.substring(0, 80)}{goalText.length > 80 ? "..." : ""}</div>
          </div>
        </div>

        {/* State Timeline */}
        <div className="space-y-2">
          {events.map((event, i) => {
            const info = STATE_LABELS[event.state] || { label: event.state, color: "bg-slate-400", icon: "·" };
            return (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className={`flex-shrink-0 w-2 h-2 rounded-full ${info.color}`}></span>
                <span className="text-slate-600 font-mono text-xs w-20">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-slate-800">{info.icon} {info.label}</span>
                {event.detail && Object.keys(event.detail).length > 0 && (
                  <span className="text-slate-400 text-xs">
                    {JSON.stringify(event.detail)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Conflict Alert */}
      {events.some(e => e.state === "CONFLICTS_DETECTED") && (
        <div className="p-6 rounded-2xl bg-orange-50 border border-orange-200 shadow-md animate-in fade-in slide-in-from-bottom-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-orange-600 font-bold">⚠️ Conflict Detected</span>
          </div>
          <p className="text-sm text-slate-700">
            Specialist agents produced conflicting outputs. The orchestrator resolved the conflict during synthesis.
          </p>
          {events.find(e => e.state === "CONFLICTS_DETECTED")?.detail?.conflicts && (
            <pre className="mt-2 p-3 bg-white rounded-lg border text-xs overflow-auto max-h-40">
              {JSON.stringify(events.find(e => e.state === "CONFLICTS_DETECTED")?.detail.conflicts, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Decomposed Tasks */}
      {tasks.length > 0 && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-lg animate-in fade-in">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Decomposed Tasks</h3>
          <div className="grid md:grid-cols-2 gap-3">
            {tasks.map((task: any, i: number) => (
              <div key={task.id || i} className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                    {task.department || "AI"}
                  </span>
                  <span className="text-xs text-slate-400">{task.priority || "Standard"}</span>
                </div>
                <p className="text-sm text-slate-800">{task.title || task.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Final Report */}
      {isTerminal && report && (
        <div className="p-6 rounded-2xl bg-white border border-emerald-200 shadow-lg animate-in fade-in slide-in-from-bottom-4">
          <h3 className="text-2xl font-semibold text-slate-900 mb-4">Executive Briefing</h3>
          
          {report.executive_summary && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-100 mb-4">
              <span className="text-sm text-emerald-600 font-semibold uppercase tracking-wider">Summary</span>
              <p className="text-emerald-900 mt-1">{report.executive_summary}</p>
            </div>
          )}

          {report.recommendations && (
            <div className="p-4 rounded-xl bg-indigo-50 border border-indigo-100 mb-4">
              <span className="text-sm text-indigo-600 font-semibold uppercase tracking-wider">Recommendations</span>
              <p className="text-indigo-900 mt-1">{report.recommendations}</p>
            </div>
          )}

          <div className="pt-4 border-t border-slate-200 flex justify-center">
            <button
              onClick={onComplete}
              className="px-8 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-700 transition-colors shadow-md"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      )}

      {/* Error State */}
      {currentState === "FAILED" && !report && (
        <div className="p-6 rounded-2xl bg-red-50 border border-red-200 shadow-md animate-in fade-in">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-red-600 font-bold">❌ Analysis Failed</span>
          </div>
          <p className="text-sm text-slate-700 mb-4">
            {error || "The orchestrator encountered an error during goal processing."}
          </p>
          <button
            onClick={onComplete}
            className="px-6 py-2 rounded-xl bg-slate-100 text-slate-900 font-medium hover:bg-slate-200 transition-colors border border-slate-200"
          >
            Return to Dashboard
          </button>
        </div>
      )}
    </div>
  );
}
