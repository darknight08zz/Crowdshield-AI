'use client';

import React from 'react';
import { Clock } from 'lucide-react';

interface Props {
  horizonSeconds?: number;
  leadTimeSeconds?: number | null;
  warningState?: string;
}

export function LeadTimeWidget({ horizonSeconds = 300, leadTimeSeconds, warningState }: Props) {
  const isElevated = warningState === 'EARLY_WARNING' || warningState === 'HIGH_RISK';

  return (
    <div className="card-command p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          MODEL WARNING HORIZON
        </span>
        <span className="text-[10px] font-mono-nums text-slate-400">Target: EARLY_ESCALATION_5M</span>
      </div>

      <div className="flex items-center justify-between font-mono-nums">
        <div className="text-xl font-extrabold text-white">
          {horizonSeconds} <span className="text-xs font-normal text-slate-400">sec (5m) horizon</span>
        </div>
        <span
          className={`px-2.5 py-0.5 text-[10px] font-extrabold rounded border ${
            isElevated
              ? 'bg-amber-950/80 text-amber-300 border-amber-500/60 animate-pulse'
              : 'bg-slate-900 text-slate-400 border-slate-800'
          }`}
        >
          {isElevated ? 'EARLY WARNING ACTIVE' : 'NOMINAL MONITORING'}
        </span>
      </div>

      {/* Visual Horizon Scale */}
      <div className="w-full h-2 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${isElevated ? 'bg-amber-400' : 'bg-cyan-500'}`}
          style={{ width: isElevated ? '100%' : '30%' }}
        />
      </div>

      <p className="text-[9px] text-slate-500 leading-tight">
        Backend temporal prediction window (300s). Physics-defined proxy model, not operationally validated.
      </p>
    </div>
  );
}
