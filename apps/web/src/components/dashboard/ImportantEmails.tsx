"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Mail, ArrowUpRight, Sparkles, X, Check, Shield, User, Clock, Reply, CornerDownRight, RefreshCw, Key, ExternalLink, AlertCircle, CheckCircle2 } from "lucide-react";

export function ImportantEmails() {
  const [activeTab, setActiveTab] = useState("All");
  const categories = ["All", "Investors", "Clients", "Board Members", "Finance", "Legal", "Partnerships"];

  const [emails, setEmails] = useState<any[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<any>(null);
  const [replyDraft, setReplyDraft] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("API Connection Required");
  const [isRealApiConnected, setIsRealApiConnected] = useState(false);
  const [isTokenExpired, setIsTokenExpired] = useState(false);

  useEffect(() => {
    checkGoogleConnection();
  }, []);

  const checkGoogleConnection = async () => {
    try {
      const chiefToken = localStorage.getItem("chief_token");
      if (!chiefToken) return;

      const payload = JSON.parse(atob(chiefToken.split('.')[1]));
      const tenantId = payload.tenant_id;

      // Check with gateway if Gmail scopes are granted
      const res = await fetch(`http://localhost:8002/auth/google/scopes?tenant_id=${tenantId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.granted && data.granted.gmail) {
          setIsRealApiConnected(true);
          setSyncStatus("Connected to Workspace via OAuth");
          fetchRealEmails(chiefToken);
        } else {
          setIsRealApiConnected(false);
          setSyncStatus("Gmail API disconnected. Connection required.");
        }
      }
    } catch (e) {
      console.warn("Failed to check Google scopes", e);
    }
  };

  const fetchRealEmails = async (token: string) => {
    setIsSyncing(true);
    setSyncStatus("Fetching live emails via Gateway...");
    try {
      const response = await fetch("http://localhost:8002/execute/read", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          provider: "google",
          operation: "get_recent_emails",
          params: { max_results: 5 }
        })
      });
      
      const data = await response.json();
      if (!response.ok) {
        setSyncStatus(`Connection failed: ${data.detail || "Unknown error"}`);
        setIsRealApiConnected(false);
        return;
      }
      
      if (data.data && data.data.emails) {
        setEmails(data.data.emails);
        setSyncStatus("Live Gmail Connected");
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
      
      window.location.href = `http://localhost:8002/auth/google/incremental?tenant_id=${tenantId}&service=gmail`;
    } catch (e) {
      console.error(e);
      alert("Please log in first to connect Gmail.");
    }
  };

  const filteredEmails = emails.filter((e) => {
    if (activeTab === "All") return true;
    return e.category === activeTab || e.time === "Live Sync";
  });

  const handleGenerateAIReply = () => {
    setIsDrafting(true);
    setTimeout(() => {
      setReplyDraft(
        `Hi ${selectedEmail.sender.split(" ")[0]},\n\nThank you for reaching out. I have reviewed your message.\n\nLet's schedule a brief sync early next week to discuss next steps.\n\nBest regards,\nFounder & CEO\ncharanchandra1006@gmail.com`
      );
      setIsDrafting(false);
    }, 800);
  };

  const handleSendReply = () => {
    alert(`Autonomous Gmail Sent to: ${selectedEmail.senderEmail}\nFrom: charanchandra1006@gmail.com\n\n${replyDraft}`);
    setSelectedEmail(null);
    setReplyDraft("");
  };

  return (
    <section className="p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden space-y-6">
      {/* Google Workspace Live Integration Bar */}
      <div className="p-3.5 rounded-xl bg-neutral-50 border border-neutral-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-black text-white shadow-2xs shrink-0">
            <Mail className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-black">Google Workspace & Gmail</span>
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
            <span>{isSyncing ? "Syncing..." : "Sync Gmail"}</span>
          </button>
          <button
            onClick={handleSyncNow}
            className="px-3 py-1.5 rounded-lg bg-black hover:bg-neutral-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
          >
            <Key className="h-3.5 w-3.5" />
            <span>Connect Gmail</span>
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-black tracking-tight">
              Important Emails & VIP Inbox
            </h3>
            <span className="px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 text-[10px] font-mono font-bold">
              {emails.filter((e) => !e.read).length} UNREAD
            </span>
          </div>
          <p className="text-xs text-neutral-500 mt-0.5">
            Zero-noise executive inbox; automatically highlights critical investor and client threads
          </p>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none border-b border-neutral-200">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveTab(cat)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
              activeTab === cat
                ? "bg-black text-white font-semibold shadow-sm"
                : "bg-neutral-100 hover:bg-neutral-200 text-neutral-600 hover:text-black border border-transparent"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Email List */}
      <div className="space-y-2.5">
        {filteredEmails.length === 0 && (
          <div className="p-10 rounded-xl bg-neutral-50 border border-dashed border-neutral-300 text-center space-y-2">
            <Mail className="h-5 w-5 text-neutral-400 mx-auto" />
            <p className="text-xs font-medium text-neutral-600">No emails connected</p>
            <p className="text-[11px] text-neutral-400">Click &quot;Connect Gmail&quot; to securely authorize your inbox via OAuth.</p>
          </div>
        )}
        {filteredEmails.map((e) => (
          <div
            key={e.id}
            onClick={() => {
              setSelectedEmail(e);
              setEmails((prev) => prev.map((item) => item.id === e.id ? { ...item, read: true } : item));
            }}
            className={`p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between gap-3 group cursor-pointer ${
              !e.read
                ? "bg-neutral-50 border-neutral-300 shadow-xs"
                : "bg-white hover:bg-neutral-50 border-neutral-200 hover:border-neutral-300 opacity-90 hover:opacity-100"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className={`h-2 w-2 rounded-full shrink-0 ${!e.read ? "bg-black" : "bg-neutral-300"}`} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-black truncate">{e.sender}</span>
                    <span className="text-[10px] text-neutral-500 font-mono truncate hidden sm:inline">• {e.role}</span>
                  </div>
                  <h4 className="text-xs font-medium text-neutral-800 group-hover:underline transition-all truncate mt-0.5">
                    {e.subject}
                  </h4>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-100 text-neutral-700 border border-neutral-200 font-semibold">
                  {e.priority}
                </span>
                <span className="text-[11px] font-mono text-neutral-400">{e.time}</span>
              </div>
            </div>

            {/* AI TL;DR Box */}
            <div className="pl-4 border-l-2 border-neutral-300 bg-neutral-100/60 p-2.5 rounded-r-xl">
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-neutral-700 font-bold mb-1">
                <Sparkles className="h-3 w-3" />
                <span>AI TL;DR Summary</span>
              </div>
              <p className="text-xs text-neutral-600 font-normal leading-relaxed line-clamp-2">
                {e.tldr}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Email Details Modal */}
      {selectedEmail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-2xl rounded-2xl bg-white border border-neutral-200 shadow-2xl p-6 relative overflow-hidden animate-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-neutral-200 shrink-0">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-black" />
                <h4 className="text-sm font-bold text-black">Executive Email Reader</h4>
              </div>
              <button
                onClick={() => {
                  setSelectedEmail(null);
                  setReplyDraft("");
                }}
                className="p-1 rounded-lg text-neutral-400 hover:text-black hover:bg-neutral-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 overflow-y-auto pr-1 flex-1">
              {/* Header metadata */}
              <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200 space-y-2 font-mono text-xs">
                <div className="flex justify-between">
                  <span className="text-neutral-500 uppercase text-[10px]">From</span>
                  <span className="text-black font-bold">{selectedEmail.sender} &lt;{selectedEmail.senderEmail}&gt;</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500 uppercase text-[10px]">To</span>
                  <span className="text-black font-bold">Charan Chandra &lt;charanchandra1006@gmail.com&gt;</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500 uppercase text-[10px]">Subject</span>
                  <span className="text-black font-bold">{selectedEmail.subject}</span>
                </div>
              </div>

              {/* AI TLDR Box */}
              <div className="p-3.5 rounded-xl bg-neutral-50 border border-neutral-200 text-xs">
                <div className="flex items-center gap-1.5 font-mono text-neutral-800 font-bold mb-1">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>AI Executive Briefing</span>
                </div>
                <p className="text-neutral-700 font-normal leading-relaxed">{selectedEmail.tldr}</p>
              </div>

              {/* Raw Email Body */}
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 block mb-1">Full Message Content</span>
                <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200 text-xs text-neutral-800 font-mono whitespace-pre-wrap leading-relaxed">
                  {selectedEmail.body}
                </div>
              </div>

              {/* Reply Section */}
              <div className="pt-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-black flex items-center gap-1.5">
                    <Reply className="h-3.5 w-3.5" />
                    <span>Draft Reply (as charanchandra1006@gmail.com)</span>
                  </span>
                  <button
                    onClick={handleGenerateAIReply}
                    disabled={isDrafting}
                    className="px-3 py-1 rounded-lg bg-neutral-100 hover:bg-neutral-200 border border-neutral-300 text-black font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {isDrafting ? (
                      <>
                        <div className="h-3 w-3 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                        <span>Drafting with AI...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>Generate AI Draft Reply</span>
                      </>
                    )}
                  </button>
                </div>

                <textarea
                  rows={5}
                  placeholder="Click 'Generate AI Draft Reply' or type your response here..."
                  value={replyDraft}
                  onChange={(e) => setReplyDraft(e.target.value)}
                  className="w-full p-3.5 rounded-xl bg-white border border-neutral-300 text-xs text-black placeholder:text-neutral-400 focus:outline-none focus:border-black font-mono leading-relaxed resize-none"
                />
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-neutral-200 flex items-center justify-end gap-3 shrink-0">
              <button
                onClick={() => {
                  setSelectedEmail(null);
                  setReplyDraft("");
                }}
                className="px-4 py-2 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium transition-colors cursor-pointer border border-neutral-300"
              >
                Close
              </button>
              <button
                onClick={handleSendReply}
                disabled={!replyDraft.trim()}
                className="px-5 py-2 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
              >
                <CornerDownRight className="h-3.5 w-3.5" />
                <span>Send Autonomous Reply</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
