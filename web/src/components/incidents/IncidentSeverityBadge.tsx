'use client';

import React from 'react';
import { AlertTriangle, Flame, Shield, ShieldCheck, HelpCircle, Activity } from 'lucide-react';

interface IncidentSeverityBadgeProps {
  warningState: string;
  className?: string;
}

export function IncidentSeverityBadge({ warningState, className = '' }: IncidentSeverityBadgeProps) {
  const upper = (warningState || 'NORMAL').toUpperCase();

  switch (upper) {
    case 'HIGH_RISK':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-rose-600/30 text-rose-300 border border-rose-500/50 shadow-md shadow-rose-950/60 ${className}`}
        >
          <Flame className="w-3 h-3 text-rose-400" />
          <span>🔴 HIGH RISK</span>
        </span>
      );
    case 'EARLY_WARNING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-amber-500/25 text-amber-300 border border-amber-500/40 ${className}`}
        >
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          <span>🟡 EARLY WARNING</span>
        </span>
      );
    case 'WATCH':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 ${className}`}
        >
          <Shield className="w-3 h-3 text-cyan-400" />
          <span>🔵 WATCH</span>
        </span>
      );
    case 'NORMAL':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 ${className}`}
        >
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>🟢 NORMAL</span>
        </span>
      );
    case 'DEGRADED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-orange-500/20 text-orange-300 border border-orange-500/40 ${className}`}
        >
          <Activity className="w-3 h-3 text-orange-400" />
          <span>⚠ DEGRADED</span>
        </span>
      );
    case 'WARMING_UP':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-blue-500/20 text-blue-300 border border-blue-500/40 ${className}`}
        >
          <HelpCircle className="w-3 h-3 text-blue-400" />
          <span>⚙ WARMING UP</span>
        </span>
      );
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-slate-800 text-slate-300 border border-slate-700 ${className}`}
        >
          <span>{warningState}</span>
        </span>
      );
  }
}
