"use client";

import React, { useState } from "react";
import { useUser, useClerk } from "@clerk/nextjs";
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
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-screen w-full bg-white text-black">
        <div className="h-6 w-6 border-2 border-neutral-300 border-t-black rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    // If not signed in, render the Clerk sign-in redirect or push them there
    if (typeof window !== "undefined") {
      window.location.href = "/sign-in";
    }
    return null;
  }

  const getInitials = (name: string) => {
    const parts = name.trim().split(" ");
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };
  const founderName = user.fullName || user.firstName || "Founder";
  const founderInitials = getInitials(founderName);
  const founderImageUrl = user.imageUrl;

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Minimalist Executive Greeting & Pulse Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm">
              <div className="flex items-center gap-3.5">
                {founderImageUrl ? (
                  <img src={founderImageUrl} alt={founderName} className="h-10 w-10 rounded-xl shadow-xs shrink-0 object-cover" />
                ) : (
                  <div className="h-10 w-10 rounded-xl bg-black text-white flex items-center justify-center font-bold text-sm shadow-xs shrink-0">
                    {founderInitials}
                  </div>
                )}
                <div>
                  <h2 className="text-base font-bold text-black tracking-tight">
                    Good morning, {user.firstName || "Founder"}.
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
        onLogout={() => signOut()}
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
