'use client';

import React, { useMemo } from 'react';
import { TemporalSample } from '@/lib/temporalHistoryStore';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Shield, Zap, AlertCircle } from 'lucide-react';

interface Props {
  history: TemporalSample[];
  aiStatus?: string;
  warningState?: string;
}

export function PhysicsVsAiRiskChart({ history, aiStatus, warningState }: Props) {
  const chartData = useMemo(() => {
    if (!history || history.length === 0) return [];
    return history.map((sample) => {
      const dateObj = new Date(sample.telemetry_timestamp);
      const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return {
        time: timeStr,
        physicsRisk: Number(sample.current_physics_risk.toFixed(1)),
        aiProbability: sample.ai_probability !== null ? Number((sample.ai_probability * 100).toFixed(0)) : null,
        isStale: sample.is_stale,
      };
    });
  }, [history]);

  const isWarmup = warningState === 'WARMING_UP' || aiStatus === 'WARMING_UP';
  const isAiUnavailable = warningState === 'DEGRADED' || aiStatus === 'AI_UNAVAILABLE';

  return (
    <div className="card-command p-5 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            TEMPORAL COMPARISON: PHYSICS RISK VS. AI PROBABILITY
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Vertically aligned dual charts comparing instantaneous spatial mechanics against 5-minute forecast trajectory
          </p>
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="h-56 flex flex-col items-center justify-center rounded-xl bg-slate-950/60 border border-slate-800 text-center p-4">
          <p className="text-xs text-slate-400">Waiting for realtime inference telemetry stream...</p>
        </div>
      ) : (
        <div className="space-y-4 font-mono-nums">
          {/* Top Chart: Current Physics Risk (0 - 100) */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-bold">
              <span className="text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-rose-400" />
                CURRENT PHYSICS RISK (0 – 100 Scale)
              </span>
              <span className="text-slate-400 text-[10px]">Instantaneous Spatial Physics</span>
            </div>
            <div className="h-28 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 9 }} />
                  <YAxis stroke="#f43f5e" tick={{ fontSize: 9 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#090d16',
                      borderColor: '#1e293b',
                      borderRadius: '0.5rem',
                      fontSize: '11px',
                    }}
                    formatter={(val: any) => [`${val} / 100`, 'Current Physics Risk']}
                  />
                  <Line
                    type="monotone"
                    dataKey="physicsRisk"
                    stroke="#f43f5e"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Bottom Chart: AI Early-Warning Escalation Probability (0 - 100%) */}
          <div className="space-y-1 pt-2 border-t border-slate-800/80">
            <div className="flex items-center justify-between text-[11px] font-bold">
              <span className="text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                AI EARLY-WARNING PROBABILITY (0 – 100% Scale)
              </span>
              <span className="text-cyan-400/80 text-[10px]">5-Minute Escalation Forecast</span>
            </div>

            {isWarmup ? (
              <div className="h-28 flex items-center justify-center bg-cyan-950/20 border border-cyan-500/30 rounded-xl p-3 text-xs text-cyan-300 font-bold animate-pulse">
                Collecting temporal history... (Temporal window warming up)
              </div>
            ) : isAiUnavailable ? (
              <div className="h-28 flex items-center justify-center bg-amber-950/20 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-300 font-bold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400" />
                AI Model Unavailable for current camera stream
              </div>
            ) : (
              <div className="h-28 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
                    <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 9 }} />
                    <YAxis stroke="#38bdf8" tick={{ fontSize: 9 }} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#090d16',
                        borderColor: '#1e293b',
                        borderRadius: '0.5rem',
                        fontSize: '11px',
                      }}
                      formatter={(val: any) => [val !== null ? `${val}%` : 'N/A', 'AI Escalation Prob']}
                    />
                    <Line
                      type="monotone"
                      dataKey="aiProbability"
                      stroke="#38bdf8"
                      strokeWidth={2.5}
                      connectNulls={false}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
