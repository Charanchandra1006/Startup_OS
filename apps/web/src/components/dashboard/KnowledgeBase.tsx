"use client";

import React, { useState } from "react";
import { BookOpen, FileText, Search, Upload, Sparkles, CheckCircle2, Shield, ArrowRight, Download, Eye, Plus, Folder, Trash2, X } from "lucide-react";

export function KnowledgeBase() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const [files, setFiles] = useState([
    {
      id: "kb-1",
      name: "Series A Term Sheet — Alpha Ventures (Revised).pdf",
      category: "Legal & Term Sheets",
      size: "2.4 MB",
      date: "Today, 11:20 AM",
      indexed: true,
      summary: "Contains 48-hour exclusivity clause, $12M equity investment at $65M pre-money valuation, 1 board seat, and standard pro-rata investor rights.",
      content: "ALPHA VENTURES — SERIES A TERM SHEET (CONFIDENTIAL)\n\nIssuer: VisionAI Technologies Inc.\nInvestment Amount: $12,000,000\nPre-Money Valuation: $65,000,000\nPost-Money Valuation: $77,000,000\n\n1. Liquidation Preference: 1x non-participating preferred stock.\n2. Board of Directors: 3 seats total (1 Founder, 1 Alpha Ventures, 1 Independent).\n3. Pro-Rata Rights: Major investors ($1M+) retain pro-rata rights in subsequent financing rounds.\n4. Exclusivity: 48-hour exclusivity window from date of execution for legal due diligence.\n\n[End of Memo]",
    },
    {
      id: "kb-2",
      name: "Q2 QuickBooks Audit & Stripe Revenue Roster.xlsx",
      category: "Finance & Ledgers",
      size: "4.1 MB",
      date: "Yesterday",
      indexed: true,
      summary: "Reconciles $124,500 daily revenue, $3.42M ARR, and confirms a net operating surplus of +$450,200 with 40.2 mo runway.",
      content: "FINANCE AGENT — Q2 REVENUE & EXPENSE RECONCILIATION\n\nStripe Gross Volume: $3,480,120\nRefunds & Chargebacks: -$60,120\nNet Monthly Revenue (MRR): $3,420,000\n\nOperating Expenses:\n- Cloud & GPU Compute (AWS / GCP / Neon): $42,100\n- Payroll & Contractor Stipends: $28,900\n- Legal & Corporate Governance: $14,000\n\nNet Cash Surplus: +$450,200\nProjected Runway at Current Burn ($85k/mo): 40.2 Months.",
    },
    {
      id: "kb-3",
      name: "CloudScale Enterprise MSA — Liability Compromise.docx",
      category: "Contracts & Agreements",
      size: "1.8 MB",
      date: "Jul 3, 2026",
      indexed: true,
      summary: "Mutual liability indemnification capped at 2x annual contract value ($360k total cap). Approved by external legal counsel.",
      content: "MUTUAL SERVICES AGREEMENT (MSA) — CLOUDSCALE INC.\n\nSection 8: Indemnification & Limitation of Liability\n\n8.1 Liability Cap: In no event shall either party's aggregate liability arising out of or related to this agreement exceed two times (2x) the total fees paid or payable by Client in the twelve (12) months preceding the claim.\n\n8.2 Exception for Data Breach: The limitation in 8.1 shall not apply to breaches of zero-trust encryption protocols or intentional gross negligence.\n\nApproved by AI Legal Agent and Sarah Jenkins (CloudScale VP Eng).",
    },
    {
      id: "kb-4",
      name: "Q3 Product Roadmap & Series A Engineering Budget.pdf",
      category: "Strategy & Roadmaps",
      size: "3.2 MB",
      date: "Jul 1, 2026",
      indexed: true,
      summary: "Detailing budget allocation for onboarding 2 Senior Backend Engineers ($150k Q3 budget). Accelerates sprint velocity by 40%.",
      content: "VISIONAI TECHNOLOGIES — Q3 PRODUCT ROADMAP & HIRING PLAN\n\nStrategic Objective: Deliver real-time multi-agent orchestration latency under 500ms before general availability.\n\nResource Requirement: Onboard 2 Senior Rust / Python Backend Engineers.\nBudget Allocation: $150,000 Q3 compensation surplus.\n\nImpact Assessment:\n- Eliminates bottleneck in WebSocket streaming gateway.\n- Extends sprint velocity by 40%.\n- Runway impact: Minimal (reduces runway from 40.2 mo to 36.4 mo).",
    },
  ]);

  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [isUploading, setIsUploading] = useState(false);

  const categories = ["All", "Legal & Term Sheets", "Finance & Ledgers", "Contracts & Agreements", "Strategy & Roadmaps"];

  const filteredFiles = files.filter((f) => {
    const matchesCat = selectedCategory === "All" || f.category === selectedCategory;
    const matchesSearch = f.name.toLowerCase().includes(searchQuery.toLowerCase()) || f.summary.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const handleSimulatedUpload = () => {
    setIsUploading(true);
    setTimeout(() => {
      const newDoc = {
        id: `kb-${Date.now()}`,
        name: `Board Briefing Deck — Series A Q3 Sync_${Math.floor(Math.random() * 100)}.pdf`,
        category: "Strategy & Roadmaps",
        size: "3.8 MB",
        date: "Just now",
        indexed: true,
        summary: "AI synthesized deck covering $3.4M ARR milestones, 40.2 mo runway, and Alpha Ventures term sheet status.",
        content: "SIMULATED EXECUTIVE BOARD DECK — Q3 2026\n\nSlide 1: Executive Summary & Revenue Velocity ($3.42M ARR, +18.4% MoM).\nSlide 2: Unit Economics (LTV/CAC at 4.8x, Net Retention 98.4%).\nSlide 3: Series A Fundraising Update ($12M term sheet at $65M pre-money).\nSlide 4: Engineering Hiring Plan (2 Senior Engineers to unblock latency roadmap).\n\nStatus: Approved for board distribution.",
      };
      setFiles([newDoc, ...files]);
      setIsUploading(false);
    }, 1000);
  };

  return (
    <section className="p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-black text-white shadow-xs">
            <BookOpen className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-black tracking-tight">
                Executive Knowledge Base & Document Vault
              </h3>
              <span className="px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 text-[10px] font-mono font-bold uppercase">
                {files.length} DOCUMENTS INDEXED
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              All company files are zero-trust encrypted and vectorized in real time for autonomous agent Retrieval-Augmented Generation (RAG)
            </p>
          </div>
        </div>

        <button
          onClick={handleSimulatedUpload}
          disabled={isUploading}
          className="px-4 py-2 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-2 transition-colors self-start sm:self-auto cursor-pointer disabled:opacity-50"
        >
          {isUploading ? (
            <>
              <div className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Indexing Document...</span>
            </>
          ) : (
            <>
              <Upload className="h-3.5 w-3.5" />
              <span>Upload & Index Document</span>
            </>
          )}
        </button>
      </div>

      {/* Filter & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-3 border-b border-neutral-200">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-xl text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
                selectedCategory === cat
                  ? "bg-black text-white font-semibold shadow-xs"
                  : "bg-neutral-100 hover:bg-neutral-200 text-neutral-600 hover:text-black border border-transparent"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
          <input
            type="text"
            placeholder="Search documents or RAG vector summaries..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-xl bg-neutral-50 border border-neutral-200 text-xs text-black placeholder:text-neutral-400 focus:outline-none focus:border-black transition-colors"
          />
        </div>
      </div>

      {/* Documents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filteredFiles.map((file) => (
          <div
            key={file.id}
            onClick={() => setSelectedFile(file)}
            className="p-4 rounded-xl bg-neutral-50 hover:bg-neutral-100/80 border border-neutral-200 hover:border-neutral-300 transition-all duration-150 flex flex-col justify-between gap-3 group cursor-pointer"
          >
            <div>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 rounded-lg bg-white border border-neutral-200 text-black shrink-0 shadow-2xs">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-bold text-black group-hover:underline transition-all truncate">
                      {file.name}
                    </h4>
                    <span className="text-[10px] font-mono text-neutral-500 uppercase">{file.category} • {file.size}</span>
                  </div>
                </div>

                <span className="px-1.5 py-0.2 rounded bg-neutral-200 text-neutral-800 border border-neutral-300 text-[9px] font-mono font-bold uppercase shrink-0 flex items-center gap-1">
                  <CheckCircle2 className="h-2.5 w-2.5 text-black" />
                  <span>RAG INDEXED</span>
                </span>
              </div>

              <div className="pl-9 text-xs text-neutral-600 font-normal leading-relaxed">
                <span className="font-mono font-bold text-black">AI Summary: </span>
                {file.summary}
              </div>
            </div>

            <div className="pl-9 pt-2 border-t border-neutral-200/80 flex items-center justify-between text-[11px] font-mono text-neutral-400">
              <span>Indexed: {file.date}</span>
              <span className="text-black group-hover:translate-x-0.5 transition-transform flex items-center gap-1 font-semibold">
                <span>View Document</span>
                <ArrowRight className="h-3 w-3" />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Document Reader Modal */}
      {selectedFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-2xl rounded-2xl bg-white border border-neutral-200 shadow-2xl p-6 relative overflow-hidden animate-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-neutral-200 shrink-0">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-black" />
                <h4 className="text-sm font-bold text-black truncate max-w-md">{selectedFile.name}</h4>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="p-1 rounded-lg text-neutral-400 hover:text-black hover:bg-neutral-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 overflow-y-auto pr-1 flex-1">
              <div className="grid grid-cols-3 gap-3 p-3 rounded-xl bg-neutral-50 border border-neutral-200 text-xs font-mono">
                <div>
                  <span className="text-neutral-400 uppercase text-[10px] block">Category</span>
                  <span className="text-black font-bold mt-0.5 block">{selectedFile.category}</span>
                </div>
                <div>
                  <span className="text-neutral-400 uppercase text-[10px] block">File Size</span>
                  <span className="text-black font-bold mt-0.5 block">{selectedFile.size}</span>
                </div>
                <div>
                  <span className="text-neutral-400 uppercase text-[10px] block">RAG Vector Status</span>
                  <span className="text-black font-bold mt-0.5 block flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3 text-black" />
                    <span>Active & Syncing</span>
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-neutral-50 border border-neutral-200 text-xs">
                <div className="flex items-center gap-1.5 font-mono text-neutral-800 font-bold mb-1">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>AI Vector Embedding Summary</span>
                </div>
                <p className="text-neutral-700 font-normal leading-relaxed">{selectedFile.summary}</p>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 block mb-1">Extracted Document Text Content</span>
                <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200 text-xs text-neutral-800 font-mono whitespace-pre-wrap leading-relaxed">
                  {selectedFile.content}
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-neutral-200 flex items-center justify-end gap-3 shrink-0">
              <button
                onClick={() => setSelectedFile(null)}
                className="px-4 py-2 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium transition-colors cursor-pointer border border-neutral-300"
              >
                Close
              </button>
              <button
                onClick={() => {
                  alert(`Downloading ${selectedFile.name}...`);
                  setSelectedFile(null);
                }}
                className="px-5 py-2 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download Original Document</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
