'use client';

import React from 'react';
import { CanonicalIncidentStatus, VALID_TRANSITIONS } from '@/types/incident';
import { CheckCircle2, Clock, Eye, ShieldAlert, XCircle, Lock } from 'lucide-react';

interface IncidentActionPanelProps {
  currentStatus: CanonicalIncidentStatus;
  onSelectAction: (targetStatus: CanonicalIncidentStatus) => void;
  disabled?: boolean;
}

export function IncidentActionPanel({
  currentStatus,
  onSelectAction,
  disabled = false,
}: IncidentActionPanelProps) {
  const allowed = VALID_TRANSITIONS[currentStatus] || [];

  if (allowed.length === 0) {
    return (
      <div className="p-3.5 rounded-xl bg-slate-950/90 border border-slate-800 text-xs text-slate-400 flex items-center justify-between font-sans">
        <div className="flex items-center space-x-2">
          <Lock className="w-4 h-4 text-slate-500" />
          <span>Incident is in terminal state <strong className="text-white">({currentStatus})</strong>.</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono-nums">No further transitions permitted.</span>
      </div>
    );
  }

  const getActionConfig = (status: CanonicalIncidentStatus) => {
    switch (status) {
      case 'ACKNOWLEDGED':
        return {
          label: 'ACKNOWLEDGE',
          icon: Clock,
          className: 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-950/40',
        };
      case 'INVESTIGATING':
        return {
          label: 'START INVESTIGATION',
          icon: Eye,
          className: 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-950/40',
        };
      case 'MITIGATING':
        return {
          label: 'START MITIGATION',
          icon: ShieldAlert,
          className: 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-950/40',
        };
      case 'RESOLVED':
        return {
          label: 'MARK RESOLVED',
          icon: CheckCircle2,
          className: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/40',
        };
      case 'FALSE_POSITIVE':
        return {
          label: 'FALSE POSITIVE',
          icon: XCircle,
          className: 'btn-secondary text-slate-300 hover:text-white',
        };
      default:
        return {
          label: status,
          icon: ShieldAlert,
          className: 'btn-secondary',
        };
    }
  };

  return (
    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
      <div className="text-[11px] font-extrabold text-slate-400 uppercase tracking-wider">
        OPERATOR ACTIONS (CURRENT STATUS: {currentStatus})
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
        {allowed.map((target) => {
          const cfg = getActionConfig(target);
          const Icon = cfg.icon;

          return (
            <button
              key={target}
              disabled={disabled}
              onClick={() => onSelectAction(target)}
              className={`py-2.5 px-3 rounded-xl font-extrabold text-xs transition flex items-center justify-center gap-2 ${cfg.className} disabled:opacity-50`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{cfg.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
