"use client";

import React, { useState } from "react";
import { Search, Bell, Settings, Sparkles, CheckCircle2, Clock, FileText, TrendingUp } from "lucide-react";
import { NavTab } from "./Sidebar";

interface TopNavProps {
  onNavigate: (tab: NavTab) => void;
  founderName?: string;
  founderInitials?: string;
}

export function TopNav({ onNavigate, founderName = "Charan Chandra", founderInitials = "CC" }: TopNavProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const notifications = [
    { id: 1, title: "Meeting starts in 15 minutes", time: "Just now", icon: Clock, type: "calendar" },
    { id: 2, title: "Revenue increased 11% today", time: "24m ago", icon: TrendingUp, type: "analytics" },
    { id: 3, title: "Investor Alpha Ventures replied", time: "1h ago", icon: Sparkles, type: "emails" },
    { id: 4, title: "Task completed: Burn rate analysis", time: "2h ago", icon: CheckCircle2, type: "tasks" },
    { id: 5, title: "New document: Series A Term Sheet.pdf", time: "4h ago", icon: FileText, type: "knowledge" },
  ];

  return (
    <header className="h-14 w-full bg-white/90 backdrop-blur-md border-b border-neutral-200 px-6 flex items-center justify-between shrink-0 sticky top-0 z-40 select-none">
      {/* Left: Search Bar */}
      <div className="flex items-center gap-4 w-96">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
          <input
            type="text"
            placeholder="Search decisions, tasks, documents (⌘K)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-xl bg-neutral-100 border border-neutral-200 text-xs text-black placeholder:text-neutral-500 focus:outline-none focus:border-black transition-colors"
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1 px-1.5 py-0.2 rounded bg-white border border-neutral-300 text-[10px] font-mono text-neutral-500 pointer-events-none shadow-xs">
            <span>⌘K</span>
          </div>
        </div>
      </div>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-3">
        {/* Notifications Button & Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className={`p-2 rounded-xl border transition-colors relative cursor-pointer ${
              showNotifications
                ? "bg-black border-black text-white"
                : "bg-neutral-100 border-neutral-200 text-neutral-600 hover:text-black hover:bg-neutral-200"
            }`}
          >
            <Bell className="h-3.5 w-3.5" />
            <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-black" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2.5 w-80 rounded-2xl bg-white border border-neutral-200 shadow-2xl p-4 z-50 animate-in fade-in duration-200">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-neutral-200">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold text-black">Notifications</h4>
                  <span className="px-1.5 py-0.2 rounded bg-black text-white text-[10px] font-mono font-bold">
                    5 New
                  </span>
                </div>
                <button
                  onClick={() => setShowNotifications(false)}
                  className="text-[11px] text-neutral-500 hover:text-black transition-colors"
                >
                  Mark all read
                </button>
              </div>

              <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                {notifications.map((n) => {
                  const Icon = n.icon;
                  return (
                    <div
                      key={n.id}
                      onClick={() => {
                        setShowNotifications(false);
                        if (n.type) onNavigate(n.type as NavTab);
                      }}
                      className="p-2.5 rounded-xl bg-neutral-50 hover:bg-neutral-100 border border-transparent hover:border-neutral-200 flex items-start gap-3 transition-colors cursor-pointer group"
                    >
                      <div className="p-1.5 rounded-lg bg-neutral-900 text-white shrink-0 mt-0.5">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-neutral-800 group-hover:text-black transition-colors truncate">
                          {n.title}
                        </p>
                        <span className="text-[10px] text-neutral-500 font-mono">{n.time}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 pt-2 border-t border-neutral-200 text-center">
                <button
                  onClick={() => {
                    setShowNotifications(false);
                    onNavigate("tasks");
                  }}
                  className="text-xs font-medium text-neutral-600 hover:text-black transition-colors"
                >
                  View Activity Feed →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Settings Button */}
        <button
          onClick={() => onNavigate("settings")}
          className="p-2 rounded-xl bg-neutral-100 border border-neutral-200 text-neutral-600 hover:text-black hover:bg-neutral-200 transition-colors cursor-pointer"
        >
          <Settings className="h-3.5 w-3.5" />
        </button>

        <div className="h-4 w-[1px] bg-neutral-200" />

        {/* Company & Profile Info */}
        <div className="flex items-center gap-2.5 pl-1">
          <div className="h-7 w-7 rounded-full bg-black text-white flex items-center justify-center text-xs font-bold shadow-xs">
            {founderInitials}
          </div>
          <div className="hidden sm:block">
            <div className="text-xs font-bold text-black flex items-center gap-1.5">
              <span>{founderName}</span>
              <span className="h-1.5 w-1.5 rounded-full bg-black" />
            </div>
            <div className="text-[10px] text-neutral-500 font-medium">VisionAI Technologies</div>
          </div>
        </div>
      </div>
    </header>
  );
}
