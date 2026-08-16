'use client';

import React from 'react';
import { Activity, User, Clock, FileText } from 'lucide-react';
import { DispatchTransition } from '@/types/dispatch';

interface DispatchTimelineProps {
  transitions: DispatchTransition[];
}

export const DispatchTimeline: React.FC<DispatchTimelineProps> = ({ transitions }) => {
  if (!transitions || transitions.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-center text-xs text-slate-500">
        No dispatch transition audit logs recorded yet.
      </div>
    );
  }

  const sorted = [...transitions].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
      {sorted.map((item) => (
        <div key={item.transition_id} className="relative group">
          <div className="absolute -left-[23px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-slate-900 ring-2 ring-blue-500 text-blue-400">
            <Activity className="h-2.5 w-2.5" />
          </div>

          <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3 text-xs shadow-sm transition-all group-hover:border-slate-700">
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-1.5 font-semibold text-white">
                <span className="text-slate-400 font-mono text-[10px]">{item.previous_status}</span>
                <span className="text-slate-500">→</span>
                <span className="text-cyan-400 font-mono">{item.new_status}</span>
              </div>
              <span className="text-[10px] text-slate-500 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {new Date(item.timestamp).toLocaleString()}
              </span>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-1">
              <span className="inline-flex items-center gap-1 rounded bg-slate-800 px-1.5 py-0.5 font-medium text-slate-300">
                <User className="h-3 w-3 text-slate-400" />
                {item.actor_type}: {item.actor_id || 'System'}
              </span>
            </div>

            {item.reason && (
              <div className="mt-2 text-slate-300 bg-slate-950/50 p-2 rounded border border-slate-800/60 flex items-start gap-1.5">
                <FileText className="h-3.5 w-3.5 text-slate-500 flex-shrink-0 mt-0.5" />
                <span className="italic">{item.reason}</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
