"use client";

import React from "react";
import { Sparkles, TrendingUp, Mail, Zap, AlertCircle, ArrowRight } from "lucide-react";

export function ExecutiveSummary() {
  const insights = [
    {
      id: 1,
      text: "Revenue increased by 12% compared to yesterday, driven by enterprise Series A expansions.",
      category: "Growth",
      icon: TrendingUp,
    },
    {
      id: 2,
      text: "Investor Alpha Ventures replied to yesterday's proposal with favorable valuation terms.",
      category: "Fundraising",
      icon: Mail,
    },
    {
      id: 3,
      text: "Marketing campaign CTR improved by 7% following the autonomous creative refresh.",
      category: "Marketing",
      icon: Zap,
    },
    {
      id: 4,
      text: "Customer churn slightly increased in SMB tier (+0.3%); proactive retention workflow dispatched.",
      category: "Retention",
      icon: AlertCircle,
    },
  ];

  return (
    <section className="p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 relative z-10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-black text-white shadow-xs">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-black tracking-tight flex items-center gap-2">
              Today&apos;s Executive Summary
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-neutral-100 text-neutral-800 border border-neutral-300 font-bold uppercase">
                AI GENERATED
              </span>
            </h3>
            <p className="text-xs text-neutral-500">Synthesized from 8 autonomous department agents over the last 24 hours</p>
          </div>
        </div>

        <span className="text-xs font-mono text-neutral-400 self-start sm:self-auto">
          Updated 10m ago
        </span>
      </div>

      {/* Insights List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 relative z-10">
        {insights.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.id}
              className="p-4 rounded-xl bg-neutral-50 hover:bg-neutral-100/80 border border-neutral-200 hover:border-neutral-300 transition-colors flex items-start gap-3.5 group cursor-default"
            >
              <div className="p-2 rounded-lg bg-white border border-neutral-200 text-black shrink-0 shadow-2xs">
                <Icon className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-neutral-500">
                    {item.category}
                  </span>
                </div>
                <p className="text-xs text-neutral-800 font-medium leading-relaxed group-hover:text-black transition-colors">
                  {item.text}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-5 pt-4 border-t border-neutral-200 flex items-center justify-between text-xs text-neutral-500 relative z-10">
        <span className="font-mono text-[11px] text-neutral-500">All departmental data streams reconciled.</span>
        <button className="text-black hover:underline font-medium flex items-center gap-1 transition-colors group cursor-pointer">
          <span>View full AI briefing</span>
          <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>
    </section>
  );
}
