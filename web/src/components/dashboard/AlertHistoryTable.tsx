'use client';

import React from 'react';
import { AlertStateTransition } from '@/lib/temporalHistoryStore';
import { OperationalWarningBadge, OperationalWarningState } from '@/components/ui/OperationalWarningBadge';
import { CameraHealthBadge, CameraHealthStatus } from '@/components/ui/CameraHealthBadge';
import { ArrowRight, History, ShieldAlert } from 'lucide-react';

interface Props {
  transitions: AlertStateTransition[];
}

export function AlertHistoryTable({ transitions }: Props) {
  return (
    <div className="card-command p-5 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <History className="w-4 h-4 text-cyan-400" />
            REALTIME ALERT TRANSITION HISTORY LOG
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Deduplicated operational warning state escalation & recovery events across monitored streams
          </p>
        </div>
      </div>

      {transitions.length === 0 ? (
        <div className="p-8 text-center rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
          <ShieldAlert className="w-8 h-8 text-slate-500 mx-auto" />
          <p className="text-xs font-semibold text-slate-300">No alert transitions logged in active session</p>
          <p className="text-[10px] text-slate-500">
            Realtime state shifts will automatically appear here as WebSocket inference updates arrive.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase">
                <th className="py-2.5 px-3">TIMESTAMP</th>
                <th className="py-2.5 px-3">ZONE / STREAM</th>
                <th className="py-2.5 px-3">PREVIOUS STATE</th>
                <th className="py-2.5 px-3">NEW STATE</th>
                <th className="py-2.5 px-3 font-mono-nums">PHYSICS RISK</th>
                <th className="py-2.5 px-3 font-mono-nums">AI PROBABILITY</th>
                <th className="py-2.5 px-3">CAMERA HEALTH</th>
                <th className="py-2.5 px-3">DATA STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {transitions.map((tr) => {
                const timeStr = new Date(tr.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                });

                return (
                  <tr key={tr.id} className="hover:bg-slate-900/40 transition">
                    <td className="py-3 px-3 font-mono-nums font-bold text-slate-300">{timeStr}</td>
                    <td className="py-3 px-3 font-semibold text-slate-200">
                      Zone {tr.zone_id.substring(0, 6)}{' '}
                      <span className="text-[10px] text-slate-500 block font-mono-nums">CAM: {tr.camera_id}</span>
                    </td>
                    <td className="py-3 px-3">
                      <OperationalWarningBadge state={tr.previous_state as OperationalWarningState} size="sm" />
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center space-x-1.5">
                        <OperationalWarningBadge state={tr.new_state as OperationalWarningState} size="sm" />
                        {tr.is_recovery && (
                          <span className="px-1.5 py-0.5 text-[9px] font-extrabold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                            RECOVERY
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 font-mono-nums font-bold text-rose-400">
                      {tr.physics_risk.toFixed(1)} / 100
                    </td>
                    <td className="py-3 px-3 font-mono-nums font-bold text-cyan-300">
                      {tr.ai_probability !== null ? `${(tr.ai_probability * 100).toFixed(0)}%` : 'N/A'}
                    </td>
                    <td className="py-3 px-3">
                      <CameraHealthBadge status={tr.camera_health as CameraHealthStatus} />
                    </td>
                    <td className="py-3 px-3">
                      {tr.is_stale ? (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-500/50">
                          STALE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-500/50">
                          LIVE
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
