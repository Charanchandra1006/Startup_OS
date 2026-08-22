"use client";

import React from "react";
import { UserButton } from "@clerk/nextjs";
import { 
  LayoutDashboard, 
  Terminal, 
  CheckSquare, 
  Mail, 
  Calendar, 
  BookOpen, 
  BarChart2, 
  FileText, 
  Settings, 
  Sparkles, 
  LogOut,
  ShieldAlert
} from "lucide-react";

export type NavTab = 
  | "dashboard" 
  | "command" 
  | "tasks" 
  | "emails" 
  | "calendar" 
  | "knowledge" 
  | "analytics" 
  | "settings";

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  onLogout: () => void;
  founderName?: string;
  founderInitials?: string;
}

export function Sidebar({ activeTab, setActiveTab, onLogout, founderName = "Charan Chandra", founderInitials = "CC" }: SidebarProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, badge: "" },
    { id: "command", label: "AI Command Center", icon: Terminal, badge: "LIVE" },
    { id: "tasks", label: "Tasks", icon: CheckSquare, badge: "148" },
    { id: "emails", label: "Emails", icon: Mail, badge: "5" },
    { id: "calendar", label: "Calendar", icon: Calendar, badge: "4" },
    { id: "knowledge", label: "Knowledge Base", icon: BookOpen, badge: "" },
    { id: "analytics", label: "Analytics", icon: BarChart2, badge: "" },
    { id: "settings", label: "Settings", icon: Settings, badge: "" },
  ];

  return (
    <aside className="w-60 h-screen bg-white border-r border-neutral-200 flex flex-col justify-between shrink-0 select-none sticky top-0">
      {/* Top Header & Branding */}
      <div className="p-5">
        <div className="flex items-center gap-3 mb-6 px-1">
          <div className="h-7 w-7 rounded-lg bg-black text-white flex items-center justify-center font-bold shrink-0 shadow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h2 className="font-bold text-xs text-black tracking-tight flex items-center gap-1.5">
              CHIEF OS
              <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 font-semibold">
                PRO
              </span>
            </h2>
            <p className="text-[11px] text-neutral-500 font-normal truncate">VisionAI Technologies</p>
          </div>
        </div>

        {/* Navigation List */}
        <div className="space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-widest text-neutral-400 px-3 py-1 font-semibold">
            Executive Suite
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as NavTab)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 cursor-pointer group ${
                  isActive
                    ? "bg-black text-white font-semibold shadow-sm"
                    : "text-neutral-600 hover:text-black hover:bg-neutral-100 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 transition-colors ${isActive ? "text-white" : "text-neutral-500 group-hover:text-black"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${
                      isActive
                        ? "bg-white text-black font-bold border-white"
                        : "bg-neutral-100 text-neutral-600 border-neutral-200"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Founder Status & Logout */}
      <div className="p-4 border-t border-neutral-200 space-y-3 bg-neutral-50">
        <div className="p-2.5 rounded-xl bg-white border border-neutral-200 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-black animate-pulse shrink-0" />
            <div>
              <div className="text-[11px] font-semibold text-black">Agents Active</div>
              <div className="text-[10px] text-neutral-500">Autonomous Mode</div>
            </div>
          </div>
          <ShieldAlert className="h-3.5 w-3.5 text-neutral-400" />
        </div>

        <div className="flex items-center justify-between px-1 pt-1">
          <div className="flex items-center gap-2.5">
            <UserButton />
            <div className="text-left">
              <div className="text-xs font-medium text-black truncate max-w-[100px]">{founderName}</div>
              <div className="text-[10px] text-neutral-500">Founder & CEO</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
