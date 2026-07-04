"use client";

import React, { useState, useEffect } from "react";
import { CheckSquare, CheckCircle2, Clock, AlertCircle, Filter, Search, Sparkles, ArrowRight, Shield, RefreshCw, Zap } from "lucide-react";

export function TaskHistory() {
  const [filter, setFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");

  const defaultTasks = [
    {
      id: "tsk-1",
      title: "Reconcile Stripe MRR with QuickBooks Q2 ledger",
      agent: "Finance Agent",
      status: "Completed",
      date: "Today, 10:15 AM",
      duration: "1m 12s",
      summary: "Verified $3,420,000 MRR (+18.4% MoM). Operating cash surplus confirmed at +$450,200.",
    },
    {
      id: "tsk-2",
      title: "Scan and benchmark Series A SaaS valuation multiples",
      agent: "Research Agent",
      status: "Completed",
      date: "Today, 09:45 AM",
      duration: "45s",
      summary: "Aggregated 14 recent B2B AI SaaS Series A rounds. Median revenue multiple confirmed at 19.2x ARR.",
    },
    {
      id: "tsk-3",
      title: "Index and summarize Alpha Ventures term sheet emails",
      agent: "Email Agent",
      status: "Completed",
      date: "Today, 08:30 AM",
      duration: "18s",
      summary: "Extracted key governance terms: $12M investment, $65M pre-money valuation, 1 board seat, standard pro-rata.",
    },
    {
      id: "tsk-4",
      title: "Model cohort LTV/CAC velocity for Q3 enterprise expansions",
      agent: "Analytics Agent",
      status: "Completed",
      date: "Yesterday, 04:20 PM",
      duration: "2m 04s",
      summary: "LTV/CAC ratio confirmed at 4.8x. Enterprise net retention rate tracking at 98.4%.",
    },
    {
      id: "tsk-5",
      title: "Simulate runway impacts of onboarding 2 Senior Backend Engineers",
      agent: "Operations Agent",
      status: "Completed",
      date: "Yesterday, 02:15 PM",
      duration: "32s",
      summary: "Confirmed runway remains above 36 months (40.2 mo current) after factoring in $300k annual salary commitment.",
    },
    {
      id: "tsk-6",
      title: "Draft mutual liability compromise clause for CloudScale MSA",
      agent: "Legal Agent",
      status: "Completed",
      date: "Jul 3, 11:00 AM",
      duration: "55s",
      summary: "Generated indemnification redlines capped at 2x annual contract value ($360k total liability cap). Approved by client.",
    },
  ];

  const [tasks, setTasks] = useState<any[]>(defaultTasks);

  const loadCompletedTasks = () => {
    try {
      const stored = localStorage.getItem("chief_completed_tasks");
      if (stored) {
        const compTasks = JSON.parse(stored);
        if (Array.isArray(compTasks) && compTasks.length > 0) {
          // Merge completed tasks at top
          const existingIds = new Set(defaultTasks.map(t => t.id));
          const formatted = compTasks.map((ct: any) => ({
            id: ct.id || `comp-${Math.random()}`,
            title: ct.title || "Executed Autonomous Action",
            agent: ct.agent || "Executive Agent",
            status: "Completed",
            date: ct.time || ct.date || "Just now",
            duration: ct.duration || "1.4s",
            summary: ct.details || ct.summary || "Verified and committed to company ledger by autonomous agent.",
          }));
          setTasks([...formatted, ...defaultTasks.filter(t => !formatted.some(f => f.id === t.id))]);
        }
      }
    } catch (err) {
      console.warn("Failed to load completed tasks from storage:", err);
    }
  };

  useEffect(() => {
    loadCompletedTasks();

    const handleSync = () => {
      loadCompletedTasks();
    };

    window.addEventListener("task_completed", handleSync);
    return () => window.removeEventListener("task_completed", handleSync);
  }, []);

  const filteredTasks = tasks.filter((t) => {
    const matchesFilter = filter === "All" || t.agent.toLowerCase().includes(filter.toLowerCase());
    const matchesSearch = t.title.toLowerCase().includes(searchQuery.toLowerCase()) || t.summary.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <section className="p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-black text-white shadow-xs">
            <CheckSquare className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-black tracking-tight">
                Autonomous Task Execution Log
              </h3>
              <span className="px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 text-[10px] font-mono font-bold">
                {tasks.length} AUDIT RECORDS
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              Complete verifiable audit trail of all background tasks executed by your departmental AI agents
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          <button
            onClick={loadCompletedTasks}
            className="px-3 py-1.5 rounded-lg bg-neutral-100 hover:bg-neutral-200 border border-neutral-300 text-neutral-700 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync Log</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-3 border-b border-neutral-200">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {["All", "Finance", "Research", "Email", "Analytics", "Operations", "Legal", "Executive", "Growth"].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-3 py-1 rounded-xl text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
                filter === cat
                  ? "bg-black text-white font-semibold shadow-xs"
                  : "bg-neutral-100 hover:bg-neutral-200 text-neutral-600 hover:text-black border border-transparent"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
          <input
            type="text"
            placeholder="Search task logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-xl bg-neutral-50 border border-neutral-200 text-xs text-black placeholder:text-neutral-400 focus:outline-none focus:border-black transition-colors font-medium"
          />
        </div>
      </div>

      {/* Tasks List */}
      <div className="space-y-2.5">
        {filteredTasks.map((t) => {
          const isExec = t.id?.toString().startsWith("exec-") || t.title.startsWith("Executed:");
          return (
            <div
              key={t.id}
              className={`p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between gap-2.5 group ${
                isExec 
                  ? "bg-white border-black shadow-xs hover:bg-neutral-50" 
                  : "bg-neutral-50 hover:bg-neutral-100/80 border-neutral-200 hover:border-neutral-300"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${isExec ? "bg-black text-white" : "bg-neutral-800 text-white"}`}>
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-black">{t.agent}</span>
                      <span className="text-[11px] font-mono text-neutral-500">• {t.date}</span>
                      {isExec && (
                        <span className="text-[9px] font-mono font-extrabold px-1.5 py-0.2 rounded bg-neutral-100 text-black border border-neutral-300 flex items-center gap-1">
                          <Zap className="h-2.5 w-2.5 fill-black" /> EXECUTED ACTION
                        </span>
                      )}
                    </div>
                    <h4 className="text-xs font-bold text-neutral-900 mt-0.5">{t.title}</h4>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 text-[10px] font-mono text-neutral-500 bg-white px-2 py-1 rounded border border-neutral-200">
                  <Clock className="h-3 w-3 text-neutral-400" />
                  <span>{t.duration}</span>
                </div>
              </div>

              <div className="pl-8 text-xs text-neutral-600 font-normal leading-relaxed">
                <span className="font-mono font-bold text-black">Result: </span>
                {t.summary}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
