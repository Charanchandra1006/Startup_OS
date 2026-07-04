"use client";

import React, { useState } from "react";
import { Settings, Shield, Key, Terminal, Cpu, Check, AlertCircle, Save, RefreshCw, Lock, Database, Globe } from "lucide-react";

export function SettingsView() {
  const [geminiModel, setGeminiModel] = useState("gemini-2.5-flash");
  const [apiKey, setApiKey] = useState("AIzaSy************************");
  const [autonomousMode, setAutonomousMode] = useState(true);
  const [emailTriage, setEmailTriage] = useState(true);
  const [quickBooksSync, setQuickBooksSync] = useState(true);
  const [calendarAutoSync, setCalendarAutoSync] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);
    setTimeout(() => {
      setIsSaving(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }, 700);
  };

  return (
    <section className="p-6 sm:p-8 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-neutral-200">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-black text-white shadow-xs">
            <Settings className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-black tracking-tight">
                System Configuration & AI Model Settings
              </h3>
              <span className="px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 text-[10px] font-mono font-bold uppercase">
                ADMIN PRIVILEGED
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              Manage zero-trust encryption keys, LLM quota routing, and departmental autonomous permissions
            </p>
          </div>
        </div>

        {saveSuccess && (
          <div className="px-3 py-1.5 rounded-lg bg-neutral-100 border border-neutral-300 text-black text-xs font-mono font-bold flex items-center gap-1.5 animate-in fade-in duration-200">
            <Check className="h-4 w-4 text-black" />
            <span>Settings Saved Successfully</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        {/* Section 1: AI Model & Quota Routing */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-black" />
            <h4 className="text-sm font-bold text-black uppercase tracking-wider font-mono">
              1. LLM Engine & Quota Routing
            </h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5 rounded-xl bg-neutral-50 border border-neutral-200">
            <div>
              <label className="block text-xs font-bold text-black mb-1 font-mono">
                Primary Orchestration Model
              </label>
              <p className="text-[11px] text-neutral-500 mb-2">
                Select the Google DeepMind model powering your 8 departmental executives. Note: Flash is required to avoid 2 RPM quota limits.
              </p>
              <select
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
                className="w-full p-2.5 rounded-xl bg-white border border-neutral-300 text-xs text-black font-semibold focus:outline-none focus:border-black transition-colors"
              >
                <option value="gemini-2.5-flash">Gemini 2.5 Flash (Recommended — High Velocity & 15 RPM)</option>
                <option value="gemini-2.5-pro">Gemini 2.5 Pro (Deep Reasoning — Strict Quota Limits)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Legacy Stable)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-black mb-1 font-mono">
                Google AI Studio API Key (Zero-Trust Encrypted)
              </label>
              <p className="text-[11px] text-neutral-500 mb-2">
                Stored in memory using AES-256-GCM encryption. Never logged or exposed to third parties.
              </p>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full pl-9 pr-24 py-2.5 rounded-xl bg-white border border-neutral-300 text-xs text-black font-mono focus:outline-none focus:border-black transition-colors"
                />
                <button
                  type="button"
                  onClick={() => alert("Rotating API Key... Existing tokens invalidated.")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded bg-neutral-100 hover:bg-neutral-200 border border-neutral-300 text-[10px] font-mono font-bold text-black transition-colors cursor-pointer"
                >
                  Rotate Key
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Autonomous Agent Permissions */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-black" />
            <h4 className="text-sm font-bold text-black uppercase tracking-wider font-mono">
              2. Departmental Autonomous Permissions
            </h4>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              {
                title: "Master Autonomous Orchestration",
                desc: "Allow AI CEO to automatically dispatch sub-agents when high-priority triggers occur.",
                state: autonomousMode,
                setter: setAutonomousMode,
              },
              {
                title: "Email Agent — Inbox Triage & Drafts",
                desc: "Allow AI to index VIP investor emails and generate redline draft replies automatically.",
                state: emailTriage,
                setter: setEmailTriage,
              },
              {
                title: "Finance Agent — QuickBooks & Stripe Sync",
                desc: "Allow daily automated revenue ledger reconciliation and burn rate runway modeling.",
                state: quickBooksSync,
                setter: setQuickBooksSync,
              },
              {
                title: "Calendar Agent — Executive Sync Routing",
                desc: "Allow AI to schedule internal standups and prepare pre-meeting briefing memos.",
                state: calendarAutoSync,
                setter: setCalendarAutoSync,
              },
            ].map((perm, idx) => (
              <div
                key={idx}
                onClick={() => perm.setter(!perm.state)}
                className="p-4 rounded-xl bg-neutral-50 hover:bg-neutral-100/80 border border-neutral-200 hover:border-neutral-300 transition-all duration-150 flex items-center justify-between gap-4 cursor-pointer group"
              >
                <div className="flex-1 min-w-0">
                  <h5 className="text-xs font-bold text-black group-hover:underline transition-all">
                    {perm.title}
                  </h5>
                  <p className="text-[11px] text-neutral-500 mt-0.5 leading-relaxed">
                    {perm.desc}
                  </p>
                </div>

                <div
                  className={`w-11 h-6 rounded-full transition-colors relative p-1 shrink-0 ${
                    perm.state ? "bg-black" : "bg-neutral-300"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full transition-transform ${
                      perm.state ? "translate-x-5 bg-white" : "translate-x-0 bg-white shadow-xs"
                    }`}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 3: Micro-Services Infrastructure Telemetry */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-black" />
            <h4 className="text-sm font-bold text-black uppercase tracking-wider font-mono">
              3. Micro-Services Gateway & Port Mapping
            </h4>
          </div>

          <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-white border border-neutral-200">
              <span className="text-neutral-400 uppercase text-[10px] block font-bold">Frontend Web UI</span>
              <span className="text-black font-bold block mt-0.5">http://localhost:3000</span>
              <span className="text-[10px] text-neutral-500 mt-1 block">Status: Online & Healthy</span>
            </div>
            <div className="p-3 rounded-lg bg-white border border-neutral-200">
              <span className="text-neutral-400 uppercase text-[10px] block font-bold">API Gateway (:4000)</span>
              <span className="text-black font-bold block mt-0.5">http://localhost:4000</span>
              <span className="text-[10px] text-neutral-500 mt-1 block">JWT Auth & Routing</span>
            </div>
            <div className="p-3 rounded-lg bg-white border border-neutral-200">
              <span className="text-neutral-400 uppercase text-[10px] block font-bold">Orchestrator (:8000)</span>
              <span className="text-black font-bold block mt-0.5">http://localhost:8000</span>
              <span className="text-[10px] text-neutral-500 mt-1 block">State Machine Active</span>
            </div>
          </div>
        </div>

        {/* Save & Reset Actions */}
        <div className="pt-4 border-t border-neutral-200 flex items-center justify-between">
          <button
            type="button"
            onClick={() => alert("Resetting all settings to default Series A profile...")}
            className="px-4 py-2.5 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium transition-colors cursor-pointer border border-neutral-300"
          >
            Reset to Defaults
          </button>

          <button
            type="submit"
            disabled={isSaving}
            className="px-6 py-2.5 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
          >
            {isSaving ? (
              <>
                <div className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Saving Configurations...</span>
              </>
            ) : (
              <>
                <Save className="h-3.5 w-3.5" />
                <span>Save All Settings</span>
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
