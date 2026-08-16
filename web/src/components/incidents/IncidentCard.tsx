'use client';

import React from 'react';
import { IncidentCanonicalData } from '@/types/incident';
import { IncidentStatusBadge } from './IncidentStatusBadge';
import { IncidentSeverityBadge } from './IncidentSeverityBadge';
import { AlertTriangle, ChevronRight, Clock, Video, MapPin } from 'lucide-react';

interface IncidentCardProps {
  incident: IncidentCanonicalData;
  isSelected?: boolean;
  onSelect: (incident: IncidentCanonicalData) => void;
}

export function IncidentCard({ incident, isSelected = false, onSelect }: IncidentCardProps) {
  const c = incident.creation_snapshot || {};
  const l = incident.latest_snapshot || {};

  const warningState = l.latest_warning_state || c.warning_state_at_creation || 'EARLY_WARNING';
  const physicsRisk = l.latest_physics_risk ?? c.physics_risk_at_creation;
  const aiProb = l.latest_ai_probability ?? c.ai_probability_at_creation;

  const formatPhysicsRisk = (val?: number | null) => {
    if (val === undefined || val === null) return 'N/A';
    return `${Math.round(val)} / 100`;
  };

  const formatAiProb = (val?: number | null) => {
    if (val === undefined || val === null) return 'N/A';
    return `${Math.round(val * 100)}%`;
  };

  const createdTime = incident.created_at
    ? new Date(incident.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'Just now';

  return (
    <div
      onClick={() => onSelect(incident)}
      className={`p-4 rounded-2xl border transition cursor-pointer space-y-3 shadow-lg ${
        isSelected
          ? 'bg-cyan-950/40 border-cyan-500/60 shadow-cyan-950/50 ring-1 ring-cyan-500/50'
          : 'bg-slate-900/90 border-slate-800/90 hover:border-slate-700 hover:bg-slate-900'
      }`}
    >
      {/* Header: Warning & Status Badges */}
      <div className="flex items-center justify-between gap-2">
        <IncidentSeverityBadge warningState={warningState} />
        <IncidentStatusBadge status={incident.status} />
      </div>

      {/* Identity & Location */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs font-black text-white font-mono-nums flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            {incident.incident_id}
          </span>
          <span className="text-[10px] text-slate-500 font-mono-nums flex items-center gap-1">
            <Clock className="w-3 h-3 text-slate-500" />
            {createdTime}
          </span>
        </div>
        <div className="text-xs text-slate-300 font-semibold flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>Zone: {incident.zone_id}</span>
          {incident.camera_id && <span className="text-slate-500">({incident.camera_id})</span>}
        </div>
      </div>

      {/* Physics Risk vs AI Probability Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs font-sans">
        <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
          <div className="text-[9px] font-extrabold text-slate-500 uppercase">PHYSICS RISK</div>
          <div className="text-xs font-black text-rose-400 font-mono-nums">
            {formatPhysicsRisk(physicsRisk)}
          </div>
        </div>

        <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
          <div className="text-[9px] font-extrabold text-slate-500 uppercase">AI PROBABILITY</div>
          <div className="text-xs font-black text-amber-300 font-mono-nums">
            {formatAiProb(aiProb)}
          </div>
        </div>
      </div>

      {/* Footer: Camera Status & Action */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-1.5 text-[10px] font-mono-nums text-slate-400">
          <Video className="w-3 h-3 text-cyan-400" />
          <span className="uppercase">{incident.camera_health_status || 'ONLINE'}</span>
          {incident.is_stale && <span className="text-amber-400 font-bold">· STALE</span>}
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelect(incident);
          }}
          className="btn-secondary py-1 px-2.5 text-[11px] inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300"
        >
          Inspect <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
