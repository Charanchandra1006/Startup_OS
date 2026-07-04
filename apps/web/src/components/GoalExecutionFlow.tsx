"use client";

import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../lib/api";

type ExecutionState = "starting" | "agents_running" | "conflict" | "report" | "executing" | "done";

export function GoalExecutionFlow({ goalText, onComplete }: { goalText: string, onComplete: () => void }) {
  const [state, setState] = useState<ExecutionState>("starting");
  const [agents, setAgents] = useState<{name: string, status: "pending" | "running" | "completed"}[]>([]);
  const [conflict, setConflict] = useState<any>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);

  useEffect(() => {
    // We only trigger this sequence for the specific pitch goal, 
    // otherwise we just complete immediately (or mock it).
    if (goalText.toLowerCase().includes("series a")) {
      const eventSource = new EventSource(`${API_BASE_URL}/demo/series-a`);
      
      eventSource.addEventListener("agents_dispatched", (e) => {
        const data = JSON.parse(e.data);
        setAgents(data.agents.map((a: string) => ({ name: a, status: "running" })));
        setState("agents_running");
      });

      eventSource.addEventListener("agents_processing", (e) => {
        const data = JSON.parse(e.data);
        setAgents(prev => prev.map(a => {
          if (data.completed.includes(a.name)) return { ...a, status: "completed" };
          return a;
        }));
      });

      eventSource.addEventListener("conflict_detected", (e) => {
        setConflict(JSON.parse(e.data));
        setState("conflict");
      });

      eventSource.addEventListener("report_generated", (e) => {
        setReportData(JSON.parse(e.data));
        setState("report");
        eventSource.close();
      });

      return () => eventSource.close();
    } else {
      // For any other goal, simulate a 2-second generic thought process then return
      setTimeout(onComplete, 2000);
    }
  }, [goalText, onComplete]);

  const handleApprove = () => {
    setState("executing");
    // Simulate real-time execution logs
    const logs = [
      "Creating Job Description for Senior Engineers...",
      "Posting to LinkedIn...",
      "Identifying top 10 candidates...",
      "Drafting outreach emails...",
      "Scheduling preliminary sync with CFO for budget allocation..."
    ];
    let i = 0;
    const interval = setInterval(() => {
      setExecutionLogs(prev => [...prev, logs[i]]);
      i++;
      if (i >= logs.length) {
        clearInterval(interval);
        setTimeout(() => setState("done"), 1500);
      }
    }, 1200);
  };

  if (state === "starting") {
    return (
      <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl animate-pulse text-indigo-600 shadow-sm">
        Initializing Chief OS Dispatcher...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Screen 3: Agent Activity */}
      {(state === "agents_running" || state === "conflict" || state === "report") && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-lg">
          <h3 className="text-lg font-medium text-slate-900 mb-4 flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              {(state === "agents_running") && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${state === "agents_running" ? 'bg-indigo-500' : 'bg-emerald-500'}`}></span>
            </span>
            Agent Activity
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {agents.map(agent => (
              <div key={agent.name} className={`p-3 rounded-xl border flex flex-col items-center justify-center gap-2 transition-colors ${agent.status === 'completed' ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}`}>
                <div className="text-sm font-medium text-slate-700">{agent.name}</div>
                {agent.status === "completed" ? (
                  <span className="text-emerald-600 font-bold text-lg">✓</span>
                ) : (
                  <span className="h-4 w-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"></span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screen 4: Conflict Resolution */}
      {(state === "conflict" || state === "report") && conflict && (
        <div className="p-6 rounded-2xl bg-orange-50 border border-orange-200 shadow-md animate-in fade-in slide-in-from-bottom-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-orange-600 font-bold">⚠️ Conflict Detected</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-white rounded-xl border border-orange-100 shadow-sm">
              <span className="text-xs text-slate-500 uppercase tracking-wider">{conflict.agent_a.name}</span>
              <p className="text-slate-800 mt-1">"{conflict.agent_a.claim}"</p>
            </div>
            <div className="p-4 bg-white rounded-xl border border-orange-100 shadow-sm">
              <span className="text-xs text-slate-500 uppercase tracking-wider">{conflict.agent_b.name}</span>
              <p className="text-slate-800 mt-1">"{conflict.agent_b.claim}"</p>
            </div>
          </div>
          {reportData?.resolution && (
            <div className="mt-4 p-4 border-l-4 border-indigo-500 bg-indigo-50 rounded-r-xl">
              <span className="text-xs text-indigo-600 font-semibold uppercase tracking-wider">Chief Resolution</span>
              <p className="text-indigo-900 mt-1">{reportData.resolution}</p>
            </div>
          )}
        </div>
      )}

      {/* Screen 5: Executive Report & Screen 6: Approval */}
      {state === "report" && reportData && (
        <div className="p-6 rounded-2xl bg-white border border-emerald-200 shadow-lg animate-in fade-in slide-in-from-bottom-4">
          <h3 className="text-2xl font-semibold text-slate-900 mb-6">Executive Briefing</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Financial Health</span>
              <p className="text-lg font-medium text-emerald-600 mt-1">{reportData.report.financial_health.status}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Hiring</span>
              <p className="text-lg font-medium text-yellow-600 mt-1">{reportData.report.hiring.status}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Engineering</span>
              <p className="text-lg font-medium text-emerald-600 mt-1">{reportData.report.engineering.status}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Legal</span>
              <p className="text-lg font-medium text-emerald-600 mt-1">{reportData.report.legal.status}</p>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-emerald-50 border border-emerald-100 mb-8">
            <span className="text-sm text-emerald-600 font-semibold uppercase tracking-wider">Top Recommendation</span>
            <p className="text-xl text-emerald-900 mt-1">{reportData.report.top_recommendation}</p>
          </div>

          <div className="pt-6 border-t border-slate-200 flex flex-col items-center justify-center gap-4">
            <p className="text-lg text-slate-700">Would you like me to execute this hiring plan?</p>
            <div className="flex gap-4">
              <button onClick={handleApprove} className="px-8 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-700 transition-colors shadow-md">
                Approve
              </button>
              <button className="px-8 py-3 rounded-xl bg-slate-100 text-slate-900 font-medium hover:bg-slate-200 transition-colors border border-slate-200">
                Modify
              </button>
              <button className="px-8 py-3 rounded-xl bg-slate-100 text-slate-900 font-medium hover:bg-red-50 transition-colors hover:text-red-600 border border-slate-200">
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Screen 7: Execution */}
      {(state === "executing" || state === "done") && (
        <div className="p-6 rounded-2xl bg-black border border-white/20 shadow-2xl animate-in zoom-in-95 duration-300">
          <h3 className="text-lg font-mono text-emerald-500 mb-4 flex items-center gap-2">
            <span className="h-2 w-2 bg-emerald-500 rounded-full animate-pulse"></span>
            CHIEF_EXECUTION_STREAM
          </h3>
          <div className="font-mono text-sm text-slate-300 space-y-2">
            {executionLogs.map((log, i) => (
              <div key={i} className="flex gap-4 animate-in slide-in-from-left-4">
                <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span>
                <span className="text-emerald-400">{log}</span>
              </div>
            ))}
            {state === "executing" && (
              <div className="flex gap-4 animate-pulse mt-2">
                <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span>
                <span className="text-slate-500">_</span>
              </div>
            )}
            {state === "done" && (
              <div className="flex gap-4 mt-4 pt-4 border-t border-white/10">
                <span className="text-emerald-400 font-bold">EXECUTION COMPLETE.</span>
                <button onClick={onComplete} className="ml-auto text-indigo-400 hover:text-indigo-300 underline underline-offset-2">
                  Return to Dashboard
                </button>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
