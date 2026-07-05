"use client";

import React, { useState, useEffect } from "react";
import { Mail, ArrowUpRight, Sparkles, X, Check, Shield, User, Clock, Reply, CornerDownRight, RefreshCw, Key, ExternalLink, AlertCircle, CheckCircle2 } from "lucide-react";

export function ImportantEmails() {
  const [activeTab, setActiveTab] = useState("All");
  const categories = ["All", "Investors", "Clients", "Board Members", "Finance", "Legal", "Partnerships"];

  const defaultEmails = [
    {
      id: "eml-1",
      sender: "Marcus Vance",
      senderEmail: "marcus@alphaventures.vc",
      role: "Managing Partner, Alpha Ventures",
      subject: "Series A Term Sheet — VisionAI Technologies",
      category: "Investors",
      time: "14m ago",
      priority: "Critical",
      tldr: "Submitted revised $12M Series A term sheet at $65M pre-money valuation. Requested 48-hour exclusivity window for legal review.",
      body: "Charan,\n\nFollowing up on yesterday's partner sync. We were extremely impressed with VisionAI's autonomous agent orchestration demo and your $3.4M ARR trajectory.\n\nAttached is our formal term sheet for a $12M Series A investment at a $65M pre-money valuation. We've agreed to standard pro-rata rights and a single board seat.\n\nPlease let us know if your legal team can review within 48 hours.\n\nBest,\nMarcus Vance",
      read: false,
    },
    {
      id: "eml-2",
      sender: "Sarah Jenkins",
      senderEmail: "s.jenkins@cloudscale.enterprise",
      role: "VP of Engineering, CloudScale Inc.",
      subject: "Enterprise MSA Approval & Onboarding Timeline",
      category: "Clients",
      time: "2h ago",
      priority: "High",
      tldr: "Approved the mutual indemnification clause for 500 enterprise seats ($180k ARR). Requesting dedicated Slack channel setup for Monday kickoff.",
      body: "Hi Charan & Team,\n\nOur legal counsel has signed off on the revised mutual liability cap. We are ready to execute the annual contract ($180,000 ARR).\n\nCould your Operations Agent spin up our shared Slack connect channel and provision API keys by Monday morning?\n\nExcited to partner,\nSarah",
      read: false,
    },
    {
      id: "eml-3",
      sender: "David K.",
      senderEmail: "david@visionai.tech",
      role: "Board Member / Seed Lead",
      subject: "Q3 Burn Rate Audit & Series A Hiring Plan",
      category: "Board Members",
      time: "Yesterday",
      priority: "Medium",
      tldr: "Reviewed AI CFO's runway simulation. Confirmed alignment on onboarding 2 Senior Backend Engineers immediately.",
      body: "Charan,\n\nI reviewed the automated QuickBooks reconciliation sent by your Finance Agent. A 40.2 month runway is exceptional given our revenue velocity.\n\nYou have my full sign-off to approve the engineering budget for the two senior hires. Let's close Alpha Ventures this week.\n\nBest,\nDavid",
      read: true,
    },
    {
      id: "eml-4",
      sender: "Google Cloud Platform",
      senderEmail: "no-reply@google.com",
      role: "Infrastructure Roster & Security Sync",
      subject: "Google Workspace & API Gateway Billing Audit",
      category: "Finance",
      time: "2d ago",
      priority: "High",
      tldr: "Monthly Google Cloud & Workspace invoice for charanchandra1006@gmail.com verified and reconciled by AI CFO.",
      body: "Hello Charan,\n\nYour Google Cloud & Workspace billing summary for account charanchandra1006@gmail.com is ready for review. All API gateway endpoints and Neon DB compute nodes remain well within your Q3 operating budget.\n\nRegards,\nGoogle Cloud Billing Team",
      read: true,
    },
  ];

  const [emails, setEmails] = useState<any[]>(defaultEmails);
  const [selectedEmail, setSelectedEmail] = useState<any>(null);
  const [replyDraft, setReplyDraft] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showGoogleModal, setShowGoogleModal] = useState(false);
  const [googleToken, setGoogleToken] = useState("");
  const [syncStatus, setSyncStatus] = useState("Connected to Workspace (charanchandra1006@gmail.com)");
  const [isRealApiConnected, setIsRealApiConnected] = useState(false);
  const [tokenSavedAt, setTokenSavedAt] = useState<number | null>(null);
  const [tokenAgeMinutes, setTokenAgeMinutes] = useState<number | null>(null);
  const [isTokenExpired, setIsTokenExpired] = useState(false);

  useEffect(() => {
    const savedToken = localStorage.getItem("google_oauth_token");
    const savedAt = localStorage.getItem("google_oauth_token_saved_at");
    if (savedToken) {
      setGoogleToken(savedToken);
      if (savedAt) {
        const savedAtMs = parseInt(savedAt, 10);
        const ageMs = Date.now() - savedAtMs;
        const ageMins = Math.floor(ageMs / 60000);
        setTokenSavedAt(savedAtMs);
        setTokenAgeMinutes(ageMins);
        if (ageMins >= 55) {
          // Token is close to or past 1-hour expiry
          setIsTokenExpired(true);
          setSyncStatus("Token expired. Please generate a new OAuth token from Google OAuth Playground.");
        } else {
          setIsRealApiConnected(true);
          fetchRealGmailData(savedToken);
        }
      } else {
        setIsRealApiConnected(true);
        fetchRealGmailData(savedToken);
      }
    }
  }, []);

  const fetchRealGmailData = async (token: string) => {
    setIsSyncing(true);
    setSyncStatus("Fetching live emails from Gmail API...");
    try {
      // Use server-side proxy to avoid CORS restrictions
      const response = await fetch("/api/google/gmail?maxResults=6", {
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

      if (data.messages && data.messages.length > 0) {
        const liveMessages = data.messages.map((msg: any) => ({
          id: msg.id,
          sender: msg.sender || "Unknown Sender",
          senderEmail: msg.senderEmail || "unknown@gmail.com",
          role: "Verified Gmail Sender",
          subject: msg.subject || "(No Subject)",
          category: "Investors",
          time: msg.dateHeader ? new Date(msg.dateHeader).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Live Sync",
          priority: msg.unread ? "High" : "Medium",
          tldr: msg.snippet,
          body: msg.snippet + "\n\n[Full message retrieved via Gmail API proxy]",
          read: !msg.unread,
        }));
        setEmails(liveMessages);
        setIsRealApiConnected(true);
        setSyncStatus(`Live Gmail API Active — ${liveMessages.length} messages loaded (charanchandra1006@gmail.com)`);
      } else {
        setSyncStatus("Gmail API connected. No messages found in inbox.");
        setIsRealApiConnected(true);
      }
    } catch (err: any) {
      console.error("Gmail proxy error:", err);
      setIsRealApiConnected(false);
      setSyncStatus(`Error: ${err.message || "Could not reach Gmail proxy. Check console."}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSyncNow = () => {
    const token = localStorage.getItem("google_oauth_token") || googleToken;
    if (token && token.trim().length > 10) {
      fetchRealGmailData(token.trim());
    } else {
      // No token saved — open the API settings modal
      setSyncStatus("No OAuth token saved. Click 'API Settings' to connect your Gmail.");
      setShowGoogleModal(true);
    }
  };

  const handleSaveToken = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = googleToken.trim();
    if (trimmed) {
      localStorage.setItem("google_oauth_token", trimmed);
      localStorage.setItem("google_oauth_token_saved_at", Date.now().toString());
      setTokenSavedAt(Date.now());
      setTokenAgeMinutes(0);
      setIsTokenExpired(false);
      setIsRealApiConnected(true);
      setShowGoogleModal(false);
      fetchRealGmailData(trimmed);
    } else {
      localStorage.removeItem("google_oauth_token");
      localStorage.removeItem("google_oauth_token_saved_at");
      setTokenSavedAt(null);
      setTokenAgeMinutes(null);
      setIsTokenExpired(false);
      setIsRealApiConnected(false);
      setShowGoogleModal(false);
      setEmails(defaultEmails);
      setSyncStatus("Connected to Workspace (charanchandra1006@gmail.com)");
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
        `Hi ${selectedEmail.sender.split(" ")[0]},\n\nThank you for reaching out. I have reviewed your message and confirmed alignment with our current operating roadmap.\n\nLet's schedule a brief sync early next week to discuss next steps.\n\nBest regards,\nCharan Chandra\nFounder & CEO, VisionAI Technologies\ncharanchandra1006@gmail.com`
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

      {/* Google Workspace API Settings Modal */}
      {showGoogleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-neutral-200 shadow-2xl p-6 relative overflow-hidden animate-in zoom-in-95 duration-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-200">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-black" />
                <h4 className="text-sm font-bold text-black">Google Gmail API Connector</h4>
              </div>
              <button
                onClick={() => setShowGoogleModal(false)}
                className="p-1 rounded-lg text-neutral-400 hover:text-black hover:bg-neutral-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Token Expiry Warning */}
            {isTokenExpired && (
              <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs space-y-1">
                <span className="font-extrabold text-red-700 block font-mono uppercase tracking-wider">Token Expired</span>
                <p className="text-red-600 leading-relaxed">
                  Your OAuth token was saved {tokenAgeMinutes ?? "60"}+ minutes ago. Google tokens expire after <strong>1 hour</strong>. You must generate a fresh token from OAuth Playground.
                </p>
              </div>
            )}

            {/* Step-by-step instructions */}
            <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200 space-y-3">
              <span className="text-[10px] font-mono font-extrabold text-black uppercase tracking-wider block">How to get a fresh token (takes 90 seconds)</span>
              <ol className="space-y-2.5">
                {[
                  { step: "1", text: "Open Google OAuth 2.0 Playground", sub: "Click the link below to open it in a new tab", action: (
                    <a
                      href="https://developers.google.com/oauthplayground/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-black text-white text-[10px] font-mono font-bold hover:bg-neutral-800 transition-colors cursor-pointer"
                    >
                      <ExternalLink className="h-3 w-3" />
                      Open OAuth Playground
                    </a>
                  ) },
                  { step: "2", text: "In Step 1: Select & authorize APIs", sub: "Search for and select this scope:", action: (
                    <code className="block text-[10px] bg-neutral-200 rounded px-2 py-1 font-mono text-black mt-1 select-all">https://www.googleapis.com/auth/gmail.readonly</code>
                  ) },
                  { step: "3", text: "Click \"Authorize APIs\" and sign in", sub: "Sign in with charanchandra1006@gmail.com when prompted.", action: null },
                  { step: "4", text: "Click \"Exchange authorization code for tokens\"", sub: "Then copy the Access Token from the response box.", action: null },
                  { step: "5", text: "Paste the Access Token below and click Connect", sub: "Tokens are valid for 1 hour. Regenerate when expired.", action: null },
                ].map(({ step, text, sub, action }) => (
                  <li key={step} className="flex items-start gap-3">
                    <span className="h-5 w-5 rounded-full bg-black text-white text-[10px] font-mono font-bold flex items-center justify-center shrink-0 mt-0.5">{step}</span>
                    <div className="min-w-0">
                      <span className="text-xs font-semibold text-black block">{text}</span>
                      <span className="text-[11px] text-neutral-500 leading-relaxed">{sub}</span>
                      {action && <div className="mt-1.5">{action}</div>}
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            <form onSubmit={handleSaveToken} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-black mb-1 font-mono">
                  Paste Access Token Here
                </label>
                <input
                  type="text"
                  value={googleToken}
                  onChange={(e) => setGoogleToken(e.target.value)}
                  placeholder="ya29.a0A..."
                  className="w-full p-3 rounded-xl bg-neutral-50 border border-neutral-300 text-xs text-black font-mono focus:outline-none focus:border-black transition-colors"
                />
                <p className="text-[10px] text-neutral-400 mt-1 font-mono">
                  Token starts with <strong>ya29.</strong> — paste the full string, do NOT include the word &quot;Bearer&quot;
                </p>
              </div>

              <div className="pt-4 border-t border-neutral-200 flex items-center justify-between gap-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setGoogleToken("");
                    localStorage.removeItem("google_oauth_token");
                    localStorage.removeItem("google_oauth_token_saved_at");
                    setIsRealApiConnected(false);
                    setIsTokenExpired(false);
                    setTokenAgeMinutes(null);
                    setEmails(defaultEmails);
                    setShowGoogleModal(false);
                    setSyncStatus("Disconnected. Showing workspace defaults.");
                  }}
                  className="px-3.5 py-2 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium transition-colors cursor-pointer border border-neutral-300"
                >
                  Disconnect
                </button>
                <button
                  type="submit"
                  disabled={!googleToken.trim()}
                  className="px-5 py-2 rounded-xl bg-black hover:bg-neutral-800 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Connect Gmail</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Email Reader & Reply Modal */}
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
