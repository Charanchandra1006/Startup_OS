"use client";

import React, { useState } from "react";

export type RiskTier = "A" | "B" | "C" | "D";

export interface ApprovalRequest {
  id: string;
  action_type: string;
  risk_tier: RiskTier;
  rationale: string;
  diff_preview: any;
  created_at: string;
}

interface ApprovalCardProps {
  request: ApprovalRequest;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
}

export function ApprovalCard({ request, onApprove, onReject }: ApprovalCardProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAction = async (action: "approve" | "reject") => {
    setIsProcessing(true);
    try {
      if (action === "approve") {
        await onApprove(request.id);
      } else {
        await onReject(request.id);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const getTierColor = (tier: RiskTier) => {
    switch (tier) {
      case "B": return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "C": return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "D": return "bg-red-500/20 text-red-400 border-red-500/30";
      default: return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    }
  };

  return (
    <div className="flex flex-col gap-4 p-5 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md transition-all hover:bg-white/10 shadow-lg">
      
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold text-white tracking-tight">
            {request.action_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </h3>
          <p className="text-sm text-white/60 mt-1">{request.rationale}</p>
        </div>
        <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${getTierColor(request.risk_tier)}`}>
          Tier {request.risk_tier}
        </span>
      </div>

      {/* Payload Preview */}
      <div className="bg-black/40 rounded-lg p-4 overflow-x-auto border border-black/20">
        <p className="text-xs text-white/40 mb-2 uppercase tracking-wider font-semibold">Execution Payload</p>
        <pre className="text-xs text-emerald-400 font-mono">
          {JSON.stringify(request.diff_preview, null, 2)}
        </pre>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mt-2">
        <button
          onClick={() => handleAction("approve")}
          disabled={isProcessing}
          className="flex-1 py-2 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-emerald-950 font-semibold transition-colors disabled:opacity-50"
        >
          {isProcessing ? "Processing..." : "Approve"}
        </button>
        <button
          onClick={() => handleAction("reject")}
          disabled={isProcessing}
          className="flex-1 py-2 px-4 rounded-lg bg-white/10 hover:bg-white/20 text-white font-semibold transition-colors disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
