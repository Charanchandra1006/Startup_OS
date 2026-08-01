"use client";

import React from "react";
import { 
  TrendingUp, 
  DollarSign, 
  Activity, 
  Users, 
  Percent, 
  Flame, 
  ShieldCheck, 
  ArrowUpRight, 
  ArrowDownRight,
  Sparkles
} from "lucide-react";

export function HealthOverview() {
  const metrics = [
    {
      label: "Today's Revenue",
      value: "—",
      change: "—",
      isPositive: true,
      icon: DollarSign,
      subtext: "Connect finance data to track",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Monthly Revenue (MRR)",
      value: "—",
      change: "—",
      isPositive: true,
      icon: Activity,
      subtext: "Connect finance data to track",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Revenue Growth %",
      value: "—",
      change: "—",
      isPositive: true,
      icon: TrendingUp,
      subtext: "Calculated after data connected",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Net Cash Flow",
      value: "—",
      change: "—",
      isPositive: true,
      icon: DollarSign,
      subtext: "Connect finance data to track",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Monthly Burn Rate",
      value: "—",
      change: "—",
      isPositive: true,
      icon: Flame,
      subtext: "Connect finance data to track",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Active Customers",
      value: "—",
      change: "—",
      isPositive: true,
      icon: Users,
      subtext: "Connect CRM to track",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Conversion Rate",
      value: "—",
      change: "—",
      isPositive: true,
      icon: Percent,
      subtext: "Connect analytics to track",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "AI Health Score",
      value: "—",
      change: "—",
      isPositive: true,
      icon: Sparkles,
      subtext: "active agents synchronized",
      chart: [0, 0, 0, 0, 0, 0, 0],
    },
  ];

  return (
    <section className="space-y-6">
      {/* Hero Header & Status Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-neutral-200 shadow-sm relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 font-semibold">
              Executive Health Overview
            </span>
            <span className="px-2 py-0.2 rounded bg-neutral-100 border border-neutral-300 text-neutral-800 text-[10px] font-mono font-bold">
              LIVE
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-black">
            Startup OS <span className="text-neutral-400 font-normal">— Dashboard</span>
          </h2>
        </div>

        {/* Status Badges */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="px-4 py-2.5 rounded-xl bg-neutral-100 border border-neutral-200 text-black flex items-center gap-2.5 shadow-xs">
            <ShieldCheck className="h-4 w-4 text-black shrink-0" />
            <div>
              <div className="text-[9px] font-mono uppercase tracking-wider text-neutral-500 font-bold">
                Overall Company Status
              </div>
              <div className="text-xs font-bold tracking-wide flex items-center gap-1.5 mt-0.5 text-black">
                <span>OPERATIONAL</span>
                <span className="h-1.5 w-1.5 rounded-full bg-black" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Grid of 9 Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((m, idx) => {
          const Icon = m.icon;
          return (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-white hover:bg-neutral-50 border border-neutral-200 hover:border-neutral-300 transition-all duration-150 shadow-xs group relative overflow-hidden flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <span className="text-[11px] font-mono text-neutral-500 uppercase tracking-wider font-semibold">
                    {m.label}
                  </span>
                  <div className="text-2xl font-bold text-black mt-1 font-mono tracking-tight">
                    {m.value}
                  </div>
                </div>
                <div className="p-2 rounded-xl bg-neutral-100 text-neutral-600 group-hover:text-black transition-colors border border-neutral-200/60">
                  <Icon className="h-4 w-4" />
                </div>
              </div>

              {/* Bottom Sparkline & Subtext */}
              <div className="flex items-end justify-between gap-4 pt-3 border-t border-neutral-100">
                <div>
                  <div className="flex items-center gap-1 text-xs font-bold text-black font-mono">
                    {m.isPositive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
                    <span>{m.change}</span>
                  </div>
                  <span className="text-[11px] text-neutral-500 truncate block mt-0.5 font-normal">
                    {m.subtext}
                  </span>
                </div>

                {/* CSS Sparkline Bars */}
                <div className="flex items-end gap-1 h-6 shrink-0 pb-0.5">
                  {m.chart.map((val, i) => (
                    <div
                      key={i}
                      style={{ height: `${val}%` }}
                      className={`w-1 rounded-t transition-all duration-300 ${
                        i === m.chart.length - 1
                          ? "bg-black"
                          : "bg-neutral-200 group-hover:bg-neutral-300"
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
