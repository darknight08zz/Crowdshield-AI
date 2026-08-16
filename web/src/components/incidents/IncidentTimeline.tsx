'use client';

import React from 'react';
import { IncidentTransitionData } from '@/types/incident';
import { IncidentStatusBadge } from './IncidentStatusBadge';
import { Bot, User, Clock, MessageSquare } from 'lucide-react';

interface IncidentTimelineProps {
  transitions: IncidentTransitionData[];
}

export function IncidentTimeline({ transitions }: IncidentTimelineProps) {
  if (!transitions || transitions.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 text-center text-xs text-slate-500 font-sans">
        No state transition records logged yet.
      </div>
    );
  }

  // Sort transitions chronologically (oldest first for audit trail view)
  const sorted = [...transitions].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider">
        <span>AUDIT & TRANSITION TIMELINE</span>
        <span className="text-[10px] text-slate-500 font-normal">Immutable Ledger</span>
      </div>

      <div className="relative pl-6 border-l border-slate-800 space-y-6">
        {sorted.map((t, idx) => {
          const isSystem = t.actor_type === 'SYSTEM';
          const formattedTime = new Date(t.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          });
          const formattedDate = new Date(t.timestamp).toLocaleDateString();

          return (
            <div key={t.transition_id || idx} className="relative group">
              {/* Timeline dot marker */}
              <div
                className={`absolute -left-[31px] top-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                  isSystem
                    ? 'bg-cyan-950 border-cyan-500 text-cyan-400'
                    : 'bg-amber-950 border-amber-500 text-amber-400'
                }`}
              >
                {isSystem ? (
                  <Bot className="w-2.5 h-2.5" />
                ) : (
                  <User className="w-2.5 h-2.5" />
                )}
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/90 shadow-md space-y-2">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 text-[10px] font-extrabold rounded ${
                        isSystem
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {isSystem ? 'SYSTEM' : `OPERATOR (${t.actor_id || 'AUTHENTICATED'})`}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono-nums flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {formattedTime} · <span className="text-[10px] text-slate-500">{formattedDate}</span>
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs pt-1">
                  <span className="text-slate-400 text-[11px] font-semibold">{t.previous_status}</span>
                  <span className="text-slate-600 font-bold">→</span>
                  <IncidentStatusBadge status={t.new_status} />
                </div>

                {t.reason && (
                  <div className="mt-2 p-2 rounded-lg bg-slate-900/90 border border-slate-800/60 text-xs text-slate-300 flex items-start gap-2">
                    <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                    <span className="italic leading-relaxed">{t.reason}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
