'use client';

import React, { useState, useMemo } from 'react';
import { TemporalSample } from '@/lib/temporalHistoryStore';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Pause, Play, Clock, Activity } from 'lucide-react';

interface Props {
  history: TemporalSample[];
  isStale?: boolean;
}

export function DensitySpeedTrendChart({ history, isStale }: Props) {
  const [timeWindowMinutes, setTimeWindowMinutes] = useState<number>(5);
  const [isLivePaused, setIsLivePaused] = useState<boolean>(false);

  // Filter history based on selected time window and pause state
  const filteredData = useMemo(() => {
    if (!history || history.length === 0) return [];

    const latestTs = new Date(history[history.length - 1].telemetry_timestamp).getTime();
    const cutoffTs = latestTs - timeWindowMinutes * 60 * 1000;

    const windowed = history.filter((s) => new Date(s.telemetry_timestamp).getTime() >= cutoffTs);

    return windowed.map((sample) => {
      const dateObj = new Date(sample.telemetry_timestamp);
      const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return {
        time: timeStr,
        rawTimestamp: sample.telemetry_timestamp,
        density: Number(sample.density.toFixed(2)),
        avgSpeed: Number(sample.average_speed.toFixed(2)),
        medianSpeed: Number(sample.median_speed.toFixed(2)),
        personCount: sample.person_count,
        isStale: sample.is_stale,
      };
    });
  }, [history, timeWindowMinutes]);

  const latestSample = history.length > 0 ? history[history.length - 1] : null;

  return (
    <div className="card-command p-5 space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            CROWD DENSITY & SPEED TEMPORAL TRENDS
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            5-Minute spatial crowd density (p/m²) vs mean pedestrian velocity (m/s)
          </p>
        </div>

        {/* Time Window & Live Pause Controls */}
        <div className="flex items-center gap-2">
          {/* Time Window Buttons */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 font-mono-nums">
            {[5, 15, 30].map((mins) => (
              <button
                key={mins}
                onClick={() => setTimeWindowMinutes(mins)}
                className={`px-2.5 py-0.5 text-[10px] font-bold rounded transition ${
                  timeWindowMinutes === mins
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {mins}M
              </button>
            ))}
          </div>

          {/* Pause Live-Follow Toggle */}
          <button
            onClick={() => setIsLivePaused(!isLivePaused)}
            className={`p-1.5 rounded-lg border text-xs font-bold transition flex items-center gap-1 ${
              isLivePaused
                ? 'bg-amber-950/60 border-amber-500/60 text-amber-300'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
            title={isLivePaused ? 'Resume live follow' : 'Pause live follow'}
          >
            {isLivePaused ? <Play className="w-3.5 h-3.5 fill-amber-300" /> : <Pause className="w-3.5 h-3.5" />}
            <span className="text-[10px] font-mono-nums">{isLivePaused ? 'PAUSED' : 'LIVE'}</span>
          </button>
        </div>
      </div>

      {/* Accessible Textual Summary for Screen Readers */}
      <div className="sr-only">
        Density trend over last {timeWindowMinutes} minutes. Current density is{' '}
        {latestSample ? latestSample.density.toFixed(2) : 'N/A'} pedestrians per square meter, average speed is{' '}
        {latestSample ? latestSample.average_speed.toFixed(2) : 'N/A'} meters per second.
      </div>

      {/* Empty State / Insufficient Data */}
      {filteredData.length === 0 ? (
        <div className="h-56 flex flex-col items-center justify-center rounded-xl bg-slate-950/60 border border-slate-800/80 text-center p-4 space-y-2">
          <Clock className="w-6 h-6 text-slate-500 animate-pulse" />
          <p className="text-xs font-semibold text-slate-400">Collecting temporal telemetry samples...</p>
          <p className="text-[10px] text-slate-500">
            Realtime WebSocket stream buffer initializing. History updates automatically as telemetry arrives.
          </p>
        </div>
      ) : (
        <div className="h-60 w-full font-mono-nums">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="left" stroke="#38bdf8" tick={{ fontSize: 10 }} domain={[0, 'auto']} />
              <YAxis yAxisId="right" orientation="right" stroke="#f43f5e" tick={{ fontSize: 10 }} domain={[0, 'auto']} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#1e293b',
                  borderRadius: '0.75rem',
                  fontSize: '11px',
                  color: '#f8fafc',
                }}
                formatter={(value: any, name: any) => {
                  if (name === 'density') return [`${value} p/m²`, 'Crowd Density'];
                  if (name === 'avgSpeed') return [`${value} m/s`, 'Average Speed'];
                  if (name === 'medianSpeed') return [`${value} m/s`, 'Median Speed'];
                  return [value, name];
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
                formatter={(value) => {
                  if (value === 'density') return <span className="text-cyan-400 font-bold">Density (p/m²)</span>;
                  if (value === 'avgSpeed') return <span className="text-rose-400 font-bold">Avg Speed (m/s)</span>;
                  if (value === 'medianSpeed') return <span className="text-amber-400 font-bold">Median Speed (m/s)</span>;
                  return value;
                }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="density"
                stroke="#38bdf8"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="avgSpeed"
                stroke="#f43f5e"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="medianSpeed"
                stroke="#f59e0b"
                strokeWidth={1.5}
                strokeDasharray="2 2"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
