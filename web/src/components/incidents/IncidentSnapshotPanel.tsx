'use client';

import React from 'react';
import { CreationSnapshotData, LatestSnapshotData } from '@/types/incident';
import { IncidentSeverityBadge } from './IncidentSeverityBadge';
import { Activity, Clock, ShieldCheck, Video, AlertTriangle } from 'lucide-react';

interface IncidentSnapshotPanelProps {
  creationSnapshot: CreationSnapshotData;
  latestSnapshot: LatestSnapshotData;
  cameraHealthStatus?: string | null;
  isStale?: boolean;
  isDegraded?: boolean;
}

export function IncidentSnapshotPanel({
  creationSnapshot,
  latestSnapshot,
  cameraHealthStatus = 'ONLINE',
  isStale = false,
  isDegraded = false,
}: IncidentSnapshotPanelProps) {
  const c = creationSnapshot || {};
  const l = latestSnapshot || {};

  const formatPhysicsRisk = (val?: number | null) => {
    if (val === undefined || val === null) return 'N/A';
    return `${Math.round(val)} / 100`;
  };

  const formatAiProb = (val?: number | null) => {
    if (val === undefined || val === null) return 'N/A';
    return `${Math.round(val * 100)}%`;
  };

  return (
    <div className="space-y-4 font-sans">
      {/* Data Quality & Camera Health Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 font-bold text-slate-300">
            <Video className="w-4 h-4 text-cyan-400" />
            <span>CAMERA:</span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] uppercase font-extrabold ${
                cameraHealthStatus === 'ONLINE'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              }`}
            >
              {cameraHealthStatus || 'ONLINE'}
            </span>
          </div>

          {isStale && (
            <span className="px-2 py-0.5 rounded text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              ⚠ STALE DATA
            </span>
          )}

          {isDegraded && (
            <span className="px-2 py-0.5 rounded text-[10px] font-black bg-orange-500/20 text-orange-300 border border-orange-500/30 flex items-center gap-1">
              <Activity className="w-3 h-3 text-orange-400" />
              DEGRADED SENSOR
            </span>
          )}
        </div>

        <div className="text-[11px] text-slate-500 font-mono-nums flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          Realtime Correlation Active
        </div>
      </div>

      {/* Grid comparing Creation vs Latest Snapshots */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Creation Snapshot Panel */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/90 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-[11px] font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              CREATION SNAPSHOT
            </div>
            <span className="text-[10px] text-slate-500 font-mono-nums">
              {c.telemetry_timestamp ? new Date(c.telemetry_timestamp).toLocaleTimeString() : 'Creation Time'}
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 font-medium">Warning State:</span>
              <IncidentSeverityBadge warningState={c.warning_state_at_creation || 'EARLY_WARNING'} />
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex justify-between items-center">
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">PHYSICS RISK</div>
                <div className="text-xs text-slate-500">Density &amp; Velocity Vector Risk</div>
              </div>
              <div className="text-sm font-black text-rose-400 font-mono-nums">
                {formatPhysicsRisk(c.physics_risk_at_creation)}
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex justify-between items-center">
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">AI EARLY WARNING PROBABILITY</div>
                <div className="text-xs text-slate-500">5-min Escalation Horizon</div>
              </div>
              <div className="text-sm font-black text-amber-300 font-mono-nums">
                {formatAiProb(c.ai_probability_at_creation)}
              </div>
            </div>
          </div>
        </div>

        {/* Latest Telemetry Snapshot Panel */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/90 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-[11px] font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              LATEST SNAPSHOT
            </div>
            <span className="text-[10px] text-slate-500 font-mono-nums">
              {l.latest_telemetry_timestamp
                ? new Date(l.latest_telemetry_timestamp).toLocaleTimeString()
                : 'Current Telemetry'}
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 font-medium">Latest Warning:</span>
              <IncidentSeverityBadge warningState={l.latest_warning_state || 'NORMAL'} />
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex justify-between items-center">
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">CURRENT PHYSICS RISK</div>
                <div className="text-xs text-slate-500">Live Crowd Kinetics</div>
              </div>
              <div className="text-sm font-black text-slate-200 font-mono-nums">
                {formatPhysicsRisk(l.latest_physics_risk)}
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/80 flex justify-between items-center">
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">CURRENT AI PROBABILITY</div>
                <div className="text-xs text-slate-500">Live Model Horizon</div>
              </div>
              <div className="text-sm font-black text-slate-200 font-mono-nums">
                {formatAiProb(l.latest_ai_probability)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
