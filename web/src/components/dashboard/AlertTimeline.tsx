'use client';

import React from 'react';
import { AlertStateTransition } from '@/lib/temporalHistoryStore';
import { OperationalWarningBadge, OperationalWarningState } from '@/components/ui/OperationalWarningBadge';
import { ArrowRight, ShieldCheck, AlertTriangle, Clock, Activity } from 'lucide-react';

interface Props {
  transitions: AlertStateTransition[];
  zoneName?: string;
}

export function AlertTimeline({ transitions, zoneName }: Props) {
  return (
    <div className="card-command p-5 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-400" />
            OPERATIONAL WARNING-STATE TIMELINE
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Deduplicated state transitions & recovery trajectory for {zoneName || 'Monitored Sector'}
          </p>
        </div>
      </div>

      {transitions.length === 0 ? (
        <div className="p-6 text-center rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
          <ShieldCheck className="w-6 h-6 text-emerald-400 mx-auto" />
          <p className="text-xs font-semibold text-slate-300">No operational state transitions recorded</p>
          <p className="text-[10px] text-slate-500">
            Sector warning state has remained steady since initial stream connection.
          </p>
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {transitions.map((t) => {
            const timeStr = new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            return (
              <div key={t.id} className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                {/* Bullet Node */}
                <div
                  className={`absolute -left-6 top-4 w-3.5 h-3.5 rounded-full border-2 bg-slate-950 ${
                    t.is_recovery ? 'border-emerald-400 text-emerald-400' : 'border-amber-400 text-amber-400'
                  }`}
                />

                {/* State Transition Flow */}
                <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                  <span className="text-xs font-bold font-mono-nums text-slate-400 mr-1">{timeStr}</span>
                  <OperationalWarningBadge state={t.previous_state as OperationalWarningState} size="sm" />
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                  <OperationalWarningBadge state={t.new_state as OperationalWarningState} size="sm" />

                  {t.is_recovery && (
                    <span className="px-2 py-0.5 text-[9px] font-extrabold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      RECOVERY
                    </span>
                  )}
                </div>

                {/* Contextual Physics & AI Metrics */}
                <div className="flex items-center space-x-3 text-[11px] font-mono-nums">
                  <span className="text-rose-400 font-bold">Physics: {t.physics_risk.toFixed(1)}</span>
                  <span className="text-cyan-300 font-bold">
                    AI: {t.ai_probability !== null ? `${(t.ai_probability * 100).toFixed(0)}%` : 'N/A'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
