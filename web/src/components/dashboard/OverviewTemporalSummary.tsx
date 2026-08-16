'use client';

import React from 'react';
import { TemporalSample } from '@/lib/temporalHistoryStore';
import { OperationalWarningBadge, OperationalWarningState } from '@/components/ui/OperationalWarningBadge';
import { TrendingUp, TrendingDown, Minus, Clock } from 'lucide-react';
import { PresentationalTrendLabel } from '@/lib/useRealtimeInference';

interface Props {
  zoneName: string;
  warningState: OperationalWarningState;
  history: TemporalSample[];
}

export function OverviewTemporalSummary({ zoneName, warningState, history }: Props) {
  if (!history || history.length < 3) {
    return (
      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
        <div className="flex items-center justify-between">
          <span className="font-bold text-slate-200">{zoneName}</span>
          <OperationalWarningBadge state={warningState} size="sm" />
        </div>
        <div className="text-[10px] text-slate-500 flex items-center gap-1.5 pt-1">
          <Clock className="w-3 h-3 text-slate-500 animate-pulse" />
          Collecting temporal trend data...
        </div>
      </div>
    );
  }

  const recent3 = history.slice(-3);

  const riskSequence = recent3.map((s) => s.current_physics_risk.toFixed(0)).join(' → ');

  const aiSequence = recent3
    .map((s) => (s.ai_probability !== null ? `${(s.ai_probability * 100).toFixed(0)}%` : 'N/A'))
    .join(' → ');

  const firstRisk = recent3[0].current_physics_risk;
  const lastRisk = recent3[recent3.length - 1].current_physics_risk;

  let trendLabel: PresentationalTrendLabel = 'STABLE';
  if (lastRisk - firstRisk > 2) trendLabel = 'ESCALATING';
  else if (lastRisk - firstRisk < -2) trendLabel = 'RECOVERING';

  return (
    <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs font-mono-nums">
      <div className="flex items-center justify-between font-sans">
        <span className="font-extrabold text-slate-200">{zoneName}</span>
        <OperationalWarningBadge state={warningState} size="sm" />
      </div>

      <div className="space-y-1 text-[11px]">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 font-sans">Physics Risk:</span>
          <span className="font-bold text-rose-400">{riskSequence}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-slate-400 font-sans">AI Probability:</span>
          <span className="font-bold text-cyan-300">{aiSequence}</span>
        </div>
      </div>

      <div className="pt-1 border-t border-slate-800/60 flex items-center justify-between font-sans text-[10px]">
        <span className="text-slate-400">Recent Trajectory:</span>
        {trendLabel === 'ESCALATING' ? (
          <span className="px-2 py-0.5 rounded font-extrabold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1">
            <TrendingUp className="w-3 h-3 text-rose-400" />
            ESCALATING
          </span>
        ) : trendLabel === 'RECOVERING' ? (
          <span className="px-2 py-0.5 rounded font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
            <TrendingDown className="w-3 h-3 text-emerald-400" />
            RECOVERING
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
            <Minus className="w-3 h-3 text-slate-400" />
            STABLE
          </span>
        )}
      </div>
    </div>
  );
}
