'use client';

import React from 'react';
import { CanonicalIncidentStatus } from '@/types/incident';
import { AlertCircle, CheckCircle2, Clock, Eye, ShieldAlert, XCircle } from 'lucide-react';

interface IncidentStatusBadgeProps {
  status: CanonicalIncidentStatus | string;
  className?: string;
}

export function IncidentStatusBadge({ status, className = '' }: IncidentStatusBadgeProps) {
  const upperStatus = (status || '').toUpperCase() as CanonicalIncidentStatus;

  switch (upperStatus) {
    case 'OPEN':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm shadow-rose-950/50 animate-pulse ${className}`}
        >
          <AlertCircle className="w-3 h-3 text-rose-400" />
          <span>OPEN</span>
        </span>
      );
    case 'ACKNOWLEDGED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40 ${className}`}
        >
          <Clock className="w-3 h-3 text-amber-400" />
          <span>ACKNOWLEDGED</span>
        </span>
      );
    case 'INVESTIGATING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 ${className}`}
        >
          <Eye className="w-3 h-3 text-cyan-400" />
          <span>INVESTIGATING</span>
        </span>
      );
    case 'MITIGATING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-purple-500/20 text-purple-300 border border-purple-500/40 ${className}`}
        >
          <ShieldAlert className="w-3 h-3 text-purple-400" />
          <span>MITIGATING</span>
        </span>
      );
    case 'RESOLVED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 ${className}`}
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>RESOLVED</span>
        </span>
      );
    case 'FALSE_POSITIVE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-slate-800 text-slate-400 border border-slate-700 ${className}`}
        >
          <XCircle className="w-3 h-3 text-slate-400" />
          <span>FALSE POSITIVE</span>
        </span>
      );
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black rounded-full uppercase bg-slate-800 text-slate-300 border border-slate-700 ${className}`}
        >
          <span>{status}</span>
        </span>
      );
  }
}
