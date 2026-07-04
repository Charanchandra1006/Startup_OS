"use client";

import React, { useState, useEffect } from "react";
import { AuthScreen } from "@/components/dashboard/AuthScreen";
import { Sidebar, NavTab } from "@/components/dashboard/Sidebar";
import { TopNav } from "@/components/dashboard/TopNav";
import { HealthOverview } from "@/components/dashboard/HealthOverview";
import { ExecutiveSummary } from "@/components/dashboard/ExecutiveSummary";
import { CommandCenter } from "@/components/dashboard/CommandCenter";
import { PendingDecisions } from "@/components/dashboard/PendingDecisions";
import { ImportantEmails } from "@/components/dashboard/ImportantEmails";
import { ScheduleTimeline } from "@/components/dashboard/ScheduleTimeline";
import { TaskHistory } from "@/components/dashboard/TaskHistory";
import { KnowledgeBase } from "@/components/dashboard/KnowledgeBase";
import { ChartsSection } from "@/components/dashboard/ChartsSection";
import { SettingsView } from "@/components/dashboard/SettingsView";

export default function FounderDashboardPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [founderName, setFounderName] = useState("Charan Chandra");
  const [founderEmail, setFounderEmail] = useState("charan@visionai.tech");

  useEffect(() => {
    const savedToken = localStorage.getItem("chief_token");
    const savedName = localStorage.getItem("chief_user_name");
    const savedEmail = localStorage.getItem("chief_user_email");
    if (savedToken) {
      if (savedName) setFounderName(savedName);
      if (savedEmail) setFounderEmail(savedEmail);
      setIsAuthenticated(true);
    }
  }, []);

  const getInitials = (name: string) => {
    const parts = name.trim().split(" ");
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };
  const founderInitials = getInitials(founderName);

  if (!isAuthenticated) {
    return (
      <AuthScreen
        onLogin={(name, email) => {
          if (name) setFounderName(name);
          if (email) setFounderEmail(email);
          setIsAuthenticated(true);
        }}
      />
    );
  }

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Minimalist Executive Greeting & Pulse Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm">
              <div className="flex items-center gap-3.5">
                <div className="h-10 w-10 rounded-xl bg-black text-white flex items-center justify-center font-bold text-sm shadow-xs shrink-0">
                  {founderInitials}
                </div>
                <div>
                  <h2 className="text-base font-bold text-black tracking-tight">
                    Good morning, {founderName.split(" ")[0]}.
                  </h2>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    Your 8 autonomous executives are active. 4 critical decisions require sign-off today.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 self-start sm:self-auto">
                <span className="px-3 py-1.5 rounded-xl bg-neutral-100 border border-neutral-200 text-black text-xs font-mono font-bold flex items-center gap-2 shadow-2xs">
                  <span className="h-2 w-2 rounded-full bg-black animate-pulse" />
                  <span>SYSTEM HEALTH: 100%</span>
                </span>
              </div>
            </div>

            {/* 1. AI Task Command Center (Core Engine) */}
            <CommandCenter onNavigate={(tab: NavTab) => setActiveTab(tab)} />

            {/* 2. Pending Critical Decisions */}
            <PendingDecisions />

            {/* 3. Daily Executive Summary */}
            <ExecutiveSummary />

            {/* 4. Executive Communications & Calendar Schedule */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ImportantEmails />
              <ScheduleTimeline />
            </div>
          </div>
        );

      case "command":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <CommandCenter onNavigate={(tab: NavTab) => setActiveTab(tab)} />
            <TaskHistory />
          </div>
        );

      case "tasks":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <PendingDecisions />
            <TaskHistory />
          </div>
        );

      case "emails":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <ImportantEmails />
          </div>
        );

      case "calendar":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <ScheduleTimeline />
          </div>
        );

      case "knowledge":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <KnowledgeBase />
          </div>
        );

      case "analytics":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <HealthOverview />
            <ChartsSection />
          </div>
        );

      case "settings":
        return (
          <div className="space-y-8 animate-in fade-in duration-300">
            <SettingsView />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen w-full bg-white text-black overflow-hidden font-sans selection:bg-neutral-200">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        founderName={founderName}
        founderInitials={founderInitials}
        onLogout={() => {
          localStorage.removeItem("chief_token");
          localStorage.removeItem("chief_user_name");
          localStorage.removeItem("chief_user_email");
          setIsAuthenticated(false);
          setActiveTab("dashboard");
        }}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-white">
        {/* Top Navigation */}
        <TopNav
          onNavigate={(tab) => setActiveTab(tab)}
          founderName={founderName}
          founderInitials={founderInitials}
        />

        {/* Scrollable Executive View */}
        <main className="flex-1 p-6 sm:p-8 overflow-y-auto max-w-7xl w-full mx-auto pb-16">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
