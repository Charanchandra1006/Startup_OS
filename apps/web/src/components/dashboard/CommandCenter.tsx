"use client";

import React, { useState, useEffect } from "react";
import { 
  Terminal, Sparkles, Play, ShieldAlert, CheckCircle2, 
  ArrowRight, Activity, Users, Zap, AlertTriangle, 
  Cpu, BarChart3, Clock, DollarSign, FileText, Check, RefreshCw, Send, Layers, ExternalLink
} from "lucide-react";
import { submitGoal, fetchGoalStatus } from "@/lib/api";

interface CommandCenterProps {
  onNavigate?: (tab: any) => void;
}

export function CommandCenter({ onNavigate }: CommandCenterProps = {}) {
  const [prompt, setPrompt] = useState("");
  const [isOrchestrating, setIsOrchestrating] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [backendGoalId, setBackendGoalId] = useState<string | null>(null);
  const [generatedTasks, setGeneratedTasks] = useState<any[]>([]);
  const [executiveReport, setExecutiveReport] = useState<any>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const [agents, setAgents] = useState<any[]>([]);

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetPrompt = prompt.trim() || "Prepare investor report and analyze last week's revenue.";
    if (!prompt.trim()) setPrompt(targetPrompt);
    
    // Submit goal to backend API in background
    let activeGoalId = "";
    try {
      const res = await submitGoal(targetPrompt);
      if (res && (res.goal_id || res.id)) {
        activeGoalId = res.goal_id || res.id;
        setBackendGoalId(activeGoalId);
      }
    } catch (err) {
      console.warn("Orchestrator backend API fallback mode:", err);
    }

    startOrchestration(targetPrompt, activeGoalId);
  };

  const startOrchestration = (targetPrompt: string, goalId?: string) => {
    setIsOrchestrating(true);
    setActiveStep(1);
    setGeneratedTasks([]);
    setExecutiveReport(null);
    setAgents([]);

    const timers: NodeJS.Timeout[] = [];

    if (goalId) {
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetchGoalStatus(goalId);
          if (!statusRes) return;

          if (statusRes.tasks && statusRes.tasks.length > 0) {
            setGeneratedTasks(statusRes.tasks);
            
            // Map the tasks to active agents
            const agentMap = new Map();
            statusRes.tasks.forEach((t: any) => {
                const dept = t.department || "AI";
                if (!agentMap.has(dept)) {
                    agentMap.set(dept, {
                        id: dept,
                        name: `${dept} Agent`,
                        role: `Assigned: ${t.title.slice(0, 35)}...`,
                        status: "Running",
                        progress: 75,
                        action: `Executing ${dept} responsibilities...`,
                        eta: "1s"
                    });
                }
            });
            setAgents(Array.from(agentMap.values()));
          }

          if (statusRes.report) {
            setExecutiveReport(statusRes.report);
          }

          const st = (statusRes.status || "").toLowerCase();
          if (st === "classifying") {
            setActiveStep(1);
          } else if (st === "decomposing") {
            setActiveStep(2);
          } else if (st === "dispatching" || st === "awaiting_specialist_output") {
            setActiveStep(4);
          } else if (st === "synthesizing") {
            setActiveStep(5);
            setAgents(prev => prev.map(a => ({ ...a, status: "Completed", progress: 100, action: "Task execution complete", eta: "0s" })));
          } else if (st === "delivered" || st === "failed" || st === "stalled" || st === "completed") {
            clearInterval(pollInterval);
            setActiveStep(6);
            setIsOrchestrating(false);
            setAgents(prev => prev.map(a => ({ ...a, status: "Completed", progress: 100, action: st === "failed" ? "Execution Failed" : "Execution Finished", eta: "0s" })));
            if (statusRes.tasks && statusRes.tasks.length > 0) {
              try {
                const existing = JSON.parse(localStorage.getItem("chief_generated_tasks") || "[]");
                const merged = [...statusRes.tasks, ...existing];
                localStorage.setItem("chief_generated_tasks", JSON.stringify(merged));
                window.dispatchEvent(new Event("tasks_generated"));
              } catch (err) {
                console.error("Failed to save generated tasks to storage:", err);
              }
            }
          }
        } catch (e) {
          // ignore polling errors
        }
      }, 1000);
      timers.push(pollInterval as any);
      return () => timers.forEach(t => clearInterval(t));
    }
  };

  const resetCommand = () => {
    setIsOrchestrating(false);
    setActiveStep(0);
    setAgents([]);
    setPrompt("");
    setBackendGoalId(null);
    setGeneratedTasks([]);
    setExecutiveReport(null);
  };

  const activeOrchestrationAgents = agents.filter(a => a.status === "Running" || a.status === "Completed");

  return (
    <section className="p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-black text-white shadow-xs shrink-0">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-black tracking-tight">
                AI Task Generator & Command Center
              </h3>
              <span className="px-2 py-0.5 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 text-[10px] font-mono font-bold uppercase">
                {isOrchestrating ? "ORCHESTRATING ACTIVE" : "READY"}
              </span>
              {backendGoalId && (
                <span className="px-2 py-0.5 rounded bg-black text-white text-[10px] font-mono font-bold uppercase">
                  API SYNCED
                </span>
              )}
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              Enter any strategic goal or prompt. Autonomous agents will decompose it into executable tasks and sync to your Tasks Board.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          {(isOrchestrating || activeStep > 0) && (
            <button
              onClick={resetCommand}
              className="px-3 py-1.5 rounded-lg bg-neutral-100 hover:bg-neutral-200 border border-neutral-300 text-neutral-700 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Reset Generator</span>
            </button>
          )}
        </div>
      </div>

      {/* Goal Input Form */}
      <form onSubmit={handleCommandSubmit} className="space-y-3">
        <div className="relative">
          <textarea
            rows={2}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isOrchestrating}
            placeholder="Type your strategic command (e.g. 'Hire 5 senior AI engineers for growth team', 'Launch Q3 marketing campaign', 'Audit Series A term sheet')..."
            className="w-full p-4 pr-32 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black focus:outline-none focus:border-black font-medium transition-colors placeholder:text-neutral-400 resize-none disabled:opacity-60 font-mono leading-relaxed"
          />
          <div className="absolute right-3 bottom-3 flex items-center gap-2">
            <button
              type="submit"
              disabled={isOrchestrating || !prompt.trim()}
              className="px-4 py-2 rounded-lg bg-black hover:bg-neutral-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isOrchestrating ? (
                <>
                  <div className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Generate Tasks</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Suggestion Chips */}
        {!isOrchestrating && activeStep === 0 && (
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="text-[11px] font-mono text-neutral-400 font-semibold">Suggested Prompts:</span>
            {[
              "Hire 5 senior AI engineers for the growth team",
              "Launch Q3 AI marketing campaign with $50k budget",
              "Audit Alpha Ventures Series A term sheet & financials",
            ].map((chip, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setPrompt(chip);
                  startOrchestration(chip);
                }}
                className="px-2.5 py-1 rounded-lg bg-neutral-100 hover:bg-neutral-200 border border-neutral-300 text-black font-medium text-[11px] transition-colors cursor-pointer text-left"
              >
                + {chip}
              </button>
            ))}
          </div>
        )}
      </form>

      {/* IDLE STATE: Clean Minimal Banner when no task is running */}
      {activeStep === 0 && !isOrchestrating && (
        <div className="p-6 rounded-xl bg-neutral-50 border border-dashed border-neutral-300 text-center space-y-2">
          <Layers className="h-6 w-6 text-neutral-400 mx-auto" />
          <h4 className="text-xs font-bold text-black">AI Task Generator Standby</h4>
          <p className="text-[11px] text-neutral-500 max-w-md mx-auto leading-relaxed">
            When you dispatch a command above, the Orchestrator will activate the relevant departmental agents to decompose your goal into executable tasks and push them to your decision board.
          </p>
        </div>
      )}

      {/* ORCHESTRATION IN PROGRESS / COMPLETED VIEW */}
      {(isOrchestrating || activeStep > 0) && (
        <div className="space-y-6 pt-2 animate-in fade-in duration-300">
          {/* Progress Header */}
          <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono font-bold">
              <span className="flex items-center gap-2 text-black">
                <Activity className={`h-4 w-4 ${isOrchestrating ? "animate-pulse" : ""}`} />
                {activeStep === 6 ? "Agents Finished • Actionable Tasks Generated" : `AI Task Decomposer Active (Phase ${activeStep} of 5)`}
              </span>
              <span className="text-neutral-500">{activeStep === 6 ? "100%" : `${Math.round((activeStep / 5) * 100)}%`}% Complete</span>
            </div>

            <div className="w-full h-2 rounded-full bg-neutral-200 overflow-hidden">
              <div 
                className="h-full bg-black transition-all duration-500 ease-out" 
                style={{ width: `${activeStep === 6 ? 100 : (activeStep / 5) * 100}%` }}
              />
            </div>
          </div>

          {/* Departmental Agent Action Grid */}
          <div className="space-y-2.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-semibold block">
              Autonomous Agent Execution Roster
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {activeOrchestrationAgents.map((agent) => {
                const isRunning = agent.status === "Running";
                const isDone = agent.status === "Completed";
                return (
                  <div
                    key={agent.id}
                    className={`p-3.5 rounded-xl border transition-all duration-200 flex items-start justify-between gap-3 ${
                      isRunning 
                        ? "bg-white border-black shadow-sm" 
                        : isDone 
                        ? "bg-neutral-50 border-neutral-200" 
                        : "bg-white border-neutral-200 opacity-60"
                    }`}
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-black">{agent.name}</span>
                        <span className="text-[10px] font-mono text-neutral-500 px-1.5 py-0.2 rounded bg-neutral-200/60 font-medium">
                          {agent.role.split("&")[0].trim()}
                        </span>
                      </div>
                      <p className="text-[11px] font-mono text-neutral-700 leading-snug truncate">
                        {agent.action}
                      </p>
                    </div>

                    <div className="shrink-0 flex items-center gap-2 self-center">
                      {isRunning ? (
                        <span className="px-2 py-0.5 rounded bg-black text-white text-[10px] font-mono font-bold uppercase animate-pulse flex items-center gap-1">
                          <Clock className="h-3 w-3 animate-spin" />
                          <span>WORKING</span>
                        </span>
                      ) : isDone ? (
                        <span className="px-2 py-0.5 rounded bg-neutral-200 text-neutral-800 text-[10px] font-mono font-bold uppercase flex items-center gap-1">
                          <Check className="h-3 w-3" />
                          <span>DONE</span>
                        </span>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* PHASE 6: ACTIONABLE GENERATED TASKS REPORT CARD */}
          {activeStep === 6 && (
            <div className="p-6 rounded-2xl bg-black text-white space-y-6 shadow-xl animate-in zoom-in-95 duration-300">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-xl bg-white text-black flex items-center justify-center font-bold">
                    <CheckCircle2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">AI Executive Task Synthesis & Ledger</h4>
                    <p className="text-xs text-neutral-400 font-mono mt-0.5">
                      Goal: &quot;{prompt}&quot;
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onNavigate && onNavigate("tasks")}
                    className="px-4 py-2 rounded-xl bg-white hover:bg-neutral-200 text-black font-bold text-xs flex items-center gap-2 shadow-sm transition-colors cursor-pointer"
                  >
                    <span>Open Tasks Board ({generatedTasks.length} Pending)</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {executiveReport && executiveReport.synthesized_answer && (
                <div className="p-5 rounded-xl bg-neutral-900 border border-neutral-800 space-y-3">
                  <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-green-400 flex items-center gap-1.5">
                      <Sparkles className="h-4 w-4 text-green-400" />
                      <span>Live Synthesized Executive Briefing</span>
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300">
                      Confidence: {executiveReport.overall_confidence || "High"}
                    </span>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-xs text-neutral-200 whitespace-pre-wrap leading-relaxed font-sans">
                    {executiveReport.synthesized_answer}
                  </div>
                  {executiveReport.caveats && executiveReport.caveats.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-neutral-800 text-[11px] text-amber-400/90 font-mono space-y-1">
                      <div className="font-bold">Caveats &amp; Notes:</div>
                      {executiveReport.caveats.map((c: string, idx: number) => (
                        <div key={idx}>&bull; {c}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Generated Actionable Tasks Box */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 font-bold flex items-center gap-1.5">
                    <Zap className="h-3.5 w-3.5 text-white" />
                    <span>Automatically Transferred to Executive Tasks Board</span>
                  </span>
                  <span className="text-xs font-mono text-neutral-400">{generatedTasks.length} Action Items Created</span>
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {generatedTasks.map((task, idx) => (
                    <div key={task.id || idx} className="p-3.5 rounded-xl bg-neutral-900 border border-neutral-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-neutral-700 transition-colors">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-white text-black text-[10px] font-mono font-bold">
                            {task.priority} Priority
                          </span>
                          <span className="text-xs font-bold text-white">{task.title}</span>
                        </div>
                        <p className="text-[11px] text-neutral-400 font-normal line-clamp-1">{task.description}</p>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <span className="text-[10px] font-mono px-2 py-1 rounded bg-neutral-800 text-neutral-300 border border-neutral-700 font-semibold">
                          Dept: {task.department}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-neutral-900 border border-neutral-800 text-xs text-neutral-300 flex items-center justify-between gap-4 font-mono">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-white shrink-0" />
                  <span>The relevant autonomous departments have synced their action items into your live workflow.</span>
                </div>
                <button
                  onClick={() => onNavigate && onNavigate("tasks")}
                  className="underline font-bold text-white hover:text-neutral-300 cursor-pointer shrink-0"
                >
                  Review & Approve in Tasks &rarr;
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
