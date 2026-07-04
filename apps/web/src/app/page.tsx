"use client";

import React, { useState, useEffect } from "react";
import { ApprovalCard, ApprovalRequest } from "../components/ApprovalCard";
import { GoalExecutionFlow } from "../components/GoalExecutionFlow";
import { fetchMetrics, fetchInsights, fetchApprovals, submitGoal, decideApproval } from "../lib/api";

export default function Home() {
  const [goal, setGoal] = useState("");
  const [submittedGoal, setSubmittedGoal] = useState("");
  const [isExecutingFlow, setIsExecutingFlow] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const [metrics, setMetrics] = useState<any>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [insights, setInsights] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const [metData, insData, appData] = await Promise.all([
          fetchMetrics().catch(() => null),
          fetchInsights().catch(() => []),
          fetchApprovals().catch(() => [])
        ]);
        if (metData) setMetrics(metData);
        if (insData) setInsights(insData);
        if (appData) setApprovals(appData);
      } catch (e) {
        console.error("Failed to load dashboard data", e);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    
    // Trigger the Pitch Demo Flow
    setSubmittedGoal(goal);
    setIsExecutingFlow(true);
    setGoal("");

    // Background submission to standard API (fire and forget for demo)
    submitGoal(goal).catch(console.error);
  };

  const handleApprove = async (id: string) => {
    await decideApproval(id, "approve");
    setApprovals(prev => prev.filter(a => a.id !== id));
  };
  const handleReject = async (id: string) => {
    await decideApproval(id, "reject");
    setApprovals(prev => prev.filter(a => a.id !== id));
  };

  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-indigo-500/30 font-sans">
      
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 flex items-center justify-between px-8 py-4 border-b border-black/5 bg-white/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">C</div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Chief OS</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-sm font-medium text-slate-900">C</div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-12 flex flex-col gap-12">
        
        {/* The Wow Factor Header */}
        <section className="flex flex-col gap-6">
          <h1 className="text-4xl md:text-5xl font-medium tracking-tight text-slate-900">
            Good Morning, Charan.
          </h1>
          
          {/* KPI Dashboard */}
          {isLoading ? (
            <div className="h-24 animate-pulse bg-black/5 rounded-2xl"></div>
          ) : metrics ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="p-4 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Company Health</p>
                <p className="text-2xl font-semibold text-emerald-600">{metrics.health_score}%</p>
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Revenue</p>
                <p className="text-2xl font-semibold text-emerald-600">↑ {metrics.revenue_growth_pct}%</p>
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Runway</p>
                <p className="text-2xl font-semibold text-slate-900">{metrics.runway_months} mo</p>
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Critical Risks</p>
                <p className="text-2xl font-semibold text-red-600">{metrics.critical_risks}</p>
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Decisions</p>
                <p className="text-2xl font-semibold text-orange-600">{metrics.decisions_waiting}</p>
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Est. Time</p>
                <p className="text-2xl font-semibold text-slate-900">{metrics.est_decision_time_mins}m</p>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-2xl border border-red-500/20 bg-red-500/10 text-red-400">
              Failed to load metrics. Ensure API Gateway and Database are running.
            </div>
          )}

          {/* Chief Conversational UI */}
          <div className="relative mt-2 p-6 rounded-2xl bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/30">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <p className="text-lg text-indigo-900 font-medium">
                  "I've already analyzed your company overnight."
                </p>
                <p className="text-sm text-indigo-700/80 mt-1">
                  I reviewed the latest Q3 financials, your pending inbox, and GitHub pull requests. There are {metrics?.decisions_waiting || 0} items needing your attention below.
                </p>
              </div>
            </div>
          </div>
        </section>

        {isExecutingFlow ? (
          <GoalExecutionFlow 
            goalText={submittedGoal} 
            onComplete={() => setIsExecutingFlow(false)} 
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 mt-4">
            
            {/* Left Column: Input & Insights */}
            <div className="lg:col-span-7 flex flex-col gap-12">
            
            {/* Goal Input Section */}
            <section className="relative">
              <form onSubmit={handleSubmit} className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-500"></div>
                <div className="relative flex bg-white rounded-2xl border border-slate-200 p-2 shadow-lg">
                  <input
                    type="text"
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    placeholder="Ask Chief to analyze data, schedule meetings, or prep documents..."
                    className="w-full bg-transparent text-lg px-4 py-3 outline-none placeholder:text-slate-400 text-slate-900"
                  />
                  <button
                    type="submit"
                    disabled={isSubmitting || !goal.trim()}
                    className="px-6 py-3 rounded-xl bg-black text-white font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                  >
                    {isSubmitting ? "Thinking..." : "Dispatch"}
                  </button>
                </div>
              </form>
            </section>

            {/* Proactive Insight Feed */}
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-medium tracking-tight text-slate-900">Overnight Briefing</h2>
                <span className="text-sm font-medium text-indigo-700 bg-indigo-50 px-3 py-1 rounded-full border border-indigo-100">{insights.length} Updates</span>
              </div>
              <div className="grid gap-4">
                {insights.length === 0 && !isLoading ? (
                  <p className="text-slate-500 italic">No new insights to report.</p>
                ) : (
                  insights.map(insight => (
                    <div key={insight.id} className="p-5 rounded-2xl bg-white border border-slate-200 hover:shadow-md transition-shadow group">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{insight.category}</span>
                        <span className="text-xs text-slate-400">{insight.time}</span>
                      </div>
                      <h3 className="text-lg font-medium text-slate-900 mb-1 group-hover:text-indigo-600 transition-colors">{insight.title}</h3>
                      <p className="text-slate-600 leading-relaxed">{insight.content}</p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>

          {/* Right Column: Approvals */}
          <div className="lg:col-span-5">
            <div className="sticky top-24">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-medium tracking-tight text-slate-900 flex items-center gap-2">
                  Decisions Waiting
                  {approvals.length > 0 && (
                    <span className="flex h-2 w-2 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500"></span>
                    </span>
                  )}
                </h2>
              </div>
              
              <div className="flex flex-col gap-4">
                {approvals.length === 0 && !isLoading ? (
                  <div className="p-8 text-center rounded-2xl border border-dashed border-slate-300 text-slate-500">
                    <p>No actions require approval right now.</p>
                  </div>
                ) : (
                  approvals.map(req => (
                    <ApprovalCard
                      key={req.id}
                      request={req}
                      onApprove={handleApprove}
                      onReject={handleReject}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

        </div>
        )}
      </main>
    </div>
  );
}
