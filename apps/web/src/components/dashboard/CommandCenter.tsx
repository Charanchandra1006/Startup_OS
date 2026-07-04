"use client";

import React, { useState, useEffect } from "react";
import { 
  Terminal, Sparkles, Play, ShieldAlert, CheckCircle2, 
  ArrowRight, Activity, Users, Zap, AlertTriangle, 
  Cpu, BarChart3, Clock, DollarSign, FileText, Check, RefreshCw, Send, Layers, ExternalLink
} from "lucide-react";
import { submitGoal } from "@/lib/api";

interface CommandCenterProps {
  onNavigate?: (tab: any) => void;
}

export function CommandCenter({ onNavigate }: CommandCenterProps = {}) {
  const [prompt, setPrompt] = useState("");
  const [isOrchestrating, setIsOrchestrating] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [backendGoalId, setBackendGoalId] = useState<string | null>(null);
  const [generatedTasks, setGeneratedTasks] = useState<any[]>([]);

  const initialAgents = [
    { id: "ceo", name: "CEO Agent", role: "Strategic Strategy & Board Alignment", status: "Waiting", progress: 0, action: "Idle; awaiting goal", eta: "--" },
    { id: "fin", name: "Finance Agent", role: "QuickBooks & Burn Rate Audit", status: "Waiting", progress: 0, action: "Idle; awaiting ledger", eta: "--" },
    { id: "ops", name: "Operations Agent", role: "Resource Allocation & Runway", status: "Waiting", progress: 0, action: "Idle; awaiting task", eta: "--" },
    { id: "eml", name: "Email Agent", role: "Investor & VIP Inbox Triage", status: "Waiting", progress: 0, action: "Idle; awaiting trigger", eta: "--" },
    { id: "cal", name: "Calendar Agent", role: "Board & Sprint Scheduling", status: "Waiting", progress: 0, action: "Idle; awaiting schedule", eta: "--" },
    { id: "rsh", name: "Research Agent", role: "Market Intel & Competitor Scan", status: "Waiting", progress: 0, action: "Idle; awaiting topic", eta: "--" },
    { id: "anl", name: "Analytics Agent", role: "Funnel Conversion & LTV Modeling", status: "Waiting", progress: 0, action: "Idle; awaiting dataset", eta: "--" },
    { id: "doc", name: "Document Agent", role: "Term Sheet & MSA Generation", status: "Waiting", progress: 0, action: "Idle; awaiting draft", eta: "--" },
  ];

  const [agents, setAgents] = useState(initialAgents);

  // Dynamic AI Task Generator Plan builder
  const generateDynamicPlan = (text: string) => {
    const lower = text.toLowerCase();
    
    if (lower.includes("hire") || lower.includes("recruit") || lower.includes("engineer") || lower.includes("hr") || lower.includes("team")) {
      return {
        theme: "Engineering & Headcount Expansion",
        actions: {
          fin: "Allocated $1.1M annual compensation budget from engineering reserves",
          eml: "Drafted personalized outreach to 15 Tier-1 engineering candidates",
          rsh: "Benchmarked AI Engineer salaries ($180k-$220k base) across SF & NYC",
          anl: "Modeled sprint velocity lift (+40%) against runway impact (-1.2 mo)",
          ops: "Provisioned 5 MacBook M3 Max hardware orders and GCP dev licenses",
          ceo: "Drafted headcount approval memo and hiring timeline for board",
          doc: "Generated proprietary IP assignment & employment agreement contracts",
          cal: "Scheduled 8 technical interview loops and debrief syncs",
        },
        tasks: [
          { id: `gen-hire-${Date.now()}-1`, title: "Approve $1.1M Engineering Headcount Compensation Budget", department: "Finance", deadline: "Today, 5:00 PM", priority: "High", description: "Finance Agent confirmed current cash reserves ($3.42M ARR, 40.2 mo runway) can absorb 5 new engineering hires while keeping runway above 36 months.", impact: "Increases product delivery velocity by 40% for Q3 Series A roadmap." },
          { id: `gen-hire-${Date.now()}-2`, title: "Sign off on IP Assignment & NDA Contract Template for New Hires", department: "Legal", deadline: "Tomorrow", priority: "Critical", description: "Legal Agent generated updated California-compliant IP assignment clauses and zero-trust NDA agreements.", impact: "Ensures 100% proprietary ownership of AI models built by new team members." },
          { id: `gen-hire-${Date.now()}-3`, title: "Review Candidate Shortlist for Lead AI Architect Role", department: "HR & Ops", deadline: "Friday", priority: "High", description: "Email and Research agents triaged 45 applicants down to top 3 Tier-1 candidates with proven LLM deployment experience.", impact: "Accelerates technical leadership onboarding by 3 weeks." },
        ]
      };
    }

    if (lower.includes("market") || lower.includes("campaign") || lower.includes("growth") || lower.includes("sales") || lower.includes("ad") || lower.includes("lead")) {
      return {
        theme: "Go-To-Market & Growth Acceleration",
        actions: {
          fin: "Reconciled $50,000 Q3 performance marketing budget allocation",
          eml: "Drafted 4-touch personalized outbound sequences for 500 enterprise leads",
          rsh: "Scanned competitor ad spend and B2B growth channels (LinkedIn/Dev)",
          anl: "Projected $140 CAC with 4.2x LTV and 350 qualified enterprise signups",
          ops: "Verified HubSpot CRM integration and lead scoring automation pipeline",
          ceo: "Synthesizing GTM expansion strategy and board growth update",
          doc: "Generated customer onboarding SLA definitions and privacy addendum",
          cal: "Scheduled weekly growth pipeline reviews with sales leadership",
        },
        tasks: [
          { id: `gen-mkt-${Date.now()}-1`, title: "Approve $50,000 Q3 Performance Ad Spend Allocation", department: "Growth", deadline: "Today, 5:00 PM", priority: "High", description: "Marketing Agent recommends deploying $50k across LinkedIn B2B and developer community sponsorships. Predicted CAC is $140.", impact: "Projected to generate ~350 qualified enterprise trial signups in 30 days." },
          { id: `gen-mkt-${Date.now()}-2`, title: "Review & Approve Enterprise Outbound Drip Sequence", department: "Sales", deadline: "Tomorrow", priority: "Medium", description: "Email Agent drafted 4-touch high-converting outbound copy targeting VP Engineering and CTO personas.", impact: "Expected to open 25+ new mid-market pipeline conversations this quarter." },
          { id: `gen-mkt-${Date.now()}-3`, title: "Sign off on New Customer Onboarding SLA Definitions", department: "Legal & Ops", deadline: "Friday", priority: "High", description: "Document Agent updated enterprise SLA guarantees to 99.9% uptime with 2-hour critical response time.", impact: "Removes procurement friction for six-figure enterprise deals." },
        ]
      };
    }

    if (lower.includes("term sheet") || lower.includes("investor") || lower.includes("series a") || lower.includes("valuation") || lower.includes("raise") || lower.includes("pitch")) {
      return {
        theme: "Series A Diligence & Term Sheet Execution",
        actions: {
          fin: "Reconciled $3.42M ARR and 40.2 mo runway metrics for data room",
          eml: "Parsed Alpha Ventures term sheet emails and redline attachments",
          rsh: "Benchmarked B2B SaaS Series A multiples (19.2x ARR confirmed)",
          anl: "Modeled cohort retention (114% NRR) and CAC payoff (8.4 mos)",
          ops: "Audited AWS/GCP compute spend and SOC2 compliance posture",
          ceo: "Synthesized board briefing memo and investor deck presentation",
          doc: "Drafted board governance redlines and valuation fallbacks",
          cal: "Synced 4 investor diligence meetings on executive schedule",
        },
        tasks: [
          { id: `gen-inv-${Date.now()}-1`, title: "Approve Redline Fallbacks for Alpha Ventures $65M Valuation Term Sheet", department: "Finance & Legal", deadline: "In 2 hours", priority: "Critical", description: "Alpha Ventures submitted a revised $12M Series A term sheet at a $65M pre-money valuation. Legal and Finance agents audited all governance clauses.", impact: "Secures 4 years of operating capital with standard founder pro-rata and board governance." },
          { id: `gen-inv-${Date.now()}-2`, title: "Sign off on Q2 Audited GAAP Financial Statements for Data Room", department: "Finance", deadline: "Tomorrow", priority: "High", description: "Finance Agent finalized GAAP revenue recognition schedules and deferred revenue accounts.", impact: "Completes financial due diligence checklist for Alpha Ventures deal team." },
          { id: `gen-inv-${Date.now()}-3`, title: "Confirm Board Meeting Schedule for Series A Final Vote", department: "Board", deadline: "Friday", priority: "High", description: "Calendar Agent aligned availability for all 5 board members for a 45-minute virtual sign-off call.", impact: "Enables formal closing and wire transfer by end of month." },
        ]
      };
    }

    // Default / Custom Goal Task Generator
    return {
      theme: "Autonomous Strategic Goal Execution",
      actions: {
        fin: `Auditing budget allocation and financial efficiency for: ${text.slice(0, 30)}`,
        eml: `Scanning stakeholder correspondence and notifications for key requirements`,
        rsh: `Gathering market benchmarks and industry best practices for execution`,
        anl: `Modeling operational impact and KPI projections (+15% efficiency lift)`,
        ops: `Checking system capacity, infrastructure resources, and security rules`,
        ceo: `Synthesizing executive action plan and dispatching instructions`,
        doc: `Generating project roadmap, compliance checklist, and brief document`,
        cal: `Scheduling milestone review syncs with department heads`,
      },
      tasks: [
        { id: `gen-custom-${Date.now()}-1`, title: `Approve Strategic Action Plan: ${text.slice(0, 38)}...`, department: "Executive", deadline: "Today, 5:00 PM", priority: "High", description: `AI CEO and Operations agents formulated an end-to-end execution roadmap with clear departmental milestones and resource budgets for: "${text}".`, impact: "Ensures aligned, rapid execution across all 8 autonomous agent teams without bottlenecking founder." },
        { id: `gen-custom-${Date.now()}-2`, title: "Review Budget & Resource Allocation for Executed Goal", department: "Finance & Ops", deadline: "Tomorrow", priority: "Medium", description: "Finance Agent verified that required spend falls within approved quarterly operating parameters.", impact: "Maintains runway stability while funding priority strategic initiative." },
        { id: `gen-custom-${Date.now()}-3`, title: "Sign off on Compliance & Documentation Package", department: "Legal & Doc", deadline: "Friday", priority: "High", description: "Document Agent generated all necessary internal memos, standard operating procedures, and audit logs.", impact: "Provides complete verifiable audit trail for company governance." },
      ]
    };
  };

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetPrompt = prompt.trim() || "Prepare investor report and analyze last week's revenue.";
    if (!prompt.trim()) setPrompt(targetPrompt);
    
    // Submit goal to backend API in background
    try {
      const res = await submitGoal(targetPrompt);
      if (res && (res.goal_id || res.id)) {
        setBackendGoalId(res.goal_id || res.id);
      }
    } catch (err) {
      console.warn("Orchestrator backend API fallback mode:", err);
    }

    startOrchestration(targetPrompt);
  };

  const startOrchestration = (targetPrompt: string) => {
    setIsOrchestrating(true);
    setActiveStep(1);
    const plan = generateDynamicPlan(targetPrompt);
    setGeneratedTasks(plan.tasks);

    setAgents(initialAgents.map(a => ({ ...a, status: "Waiting", progress: 0, action: "Queued for execution", eta: "4s" })));

    const timers: NodeJS.Timeout[] = [];

    timers.push(setTimeout(() => {
      setAgents(prev => prev.map(a => a.id === "fin" ? { ...a, status: "Completed", progress: 100, action: plan.actions.fin, eta: "0s" } : a));
      setActiveStep(2);
      setAgents(prev => prev.map(a => 
        a.id === "eml" ? { ...a, status: "Running", progress: 50, action: plan.actions.eml, eta: "2s" } :
        a.id === "rsh" ? { ...a, status: "Running", progress: 35, action: plan.actions.rsh, eta: "3s" } : a
      ));
    }, 1800));

    timers.push(setTimeout(() => {
      setAgents(prev => prev.map(a => 
        a.id === "eml" ? { ...a, status: "Completed", progress: 100, action: plan.actions.eml, eta: "0s" } :
        a.id === "rsh" ? { ...a, status: "Completed", progress: 100, action: plan.actions.rsh, eta: "0s" } :
        a.id === "anl" ? { ...a, status: "Running", progress: 60, action: plan.actions.anl, eta: "2s" } :
        a.id === "ops" ? { ...a, status: "Running", progress: 50, action: plan.actions.ops, eta: "2s" } : a
      ));
      setActiveStep(4);
    }, 3600));

    timers.push(setTimeout(() => {
      setAgents(prev => prev.map(a => 
        a.id === "anl" ? { ...a, status: "Completed", progress: 100, action: plan.actions.anl, eta: "0s" } :
        a.id === "ops" ? { ...a, status: "Completed", progress: 100, action: plan.actions.ops, eta: "0s" } :
        a.id === "ceo" ? { ...a, status: "Running", progress: 75, action: plan.actions.ceo, eta: "1s" } :
        a.id === "doc" ? { ...a, status: "Running", progress: 65, action: plan.actions.doc, eta: "1s" } :
        a.id === "cal" ? { ...a, status: "Completed", progress: 100, action: plan.actions.cal, eta: "0s" } : a
      ));
      setActiveStep(5);
    }, 5400));

    timers.push(setTimeout(() => {
      setAgents(prev => prev.map(a => ({
        ...a,
        status: "Completed",
        progress: 100,
        action: plan.actions[a.id as keyof typeof plan.actions] || "Executed flawlessly; tasks generated",
        eta: "0s"
      })));
      setActiveStep(6);
      setIsOrchestrating(false);

      // Save generated tasks to localStorage and dispatch custom event for Tasks board sync
      try {
        const existing = JSON.parse(localStorage.getItem("chief_generated_tasks") || "[]");
        const merged = [...plan.tasks, ...existing];
        localStorage.setItem("chief_generated_tasks", JSON.stringify(merged));
        window.dispatchEvent(new Event("tasks_generated"));
      } catch (err) {
        console.error("Failed to save generated tasks to storage:", err);
      }
    }, 7200));

    return () => timers.forEach(t => clearTimeout(t));
  };

  const resetCommand = () => {
    setIsOrchestrating(false);
    setActiveStep(0);
    setAgents(initialAgents);
    setPrompt("");
    setBackendGoalId(null);
    setGeneratedTasks([]);
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
                {isOrchestrating ? "ORCHESTRATING ACTIVE" : "8 AGENTS READY"}
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
            When you dispatch a command above, the Orchestrator will activate all 8 departmental agents to decompose your goal into executable tasks and push them to your decision board.
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
                {activeStep === 6 ? "All 8 Agents Finished • Actionable Tasks Generated" : `AI Task Decomposer Active (Phase ${activeStep} of 5)`}
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
                  <span>All 8 autonomous departments have synced their action items into your live workflow.</span>
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
