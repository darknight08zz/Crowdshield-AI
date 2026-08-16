'use client';

import React, { useMemo } from 'react';
import { TemporalSample } from '@/lib/temporalHistoryStore';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Users, ArrowUpDown } from 'lucide-react';

interface Props {
  history: TemporalSample[];
}

export function PersonCountFlowChart({ history }: Props) {
  const chartData = useMemo(() => {
    if (!history || history.length === 0) return [];
    return history.map((sample) => {
      const dateObj = new Date(sample.telemetry_timestamp);
      const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return {
        time: timeStr,
        personCount: sample.person_count,
        inflow: Number(sample.inflow_rate.toFixed(0)),
        outflow: Number(sample.outflow_rate.toFixed(0)),
        flowImbalance: Number(sample.flow_imbalance.toFixed(0)),
      };
    });
  }, [history]);

  return (
    <div className="card-command p-5 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
            <ArrowUpDown className="w-4 h-4 text-emerald-400" />
            CROWD VOLUME & INFLOW / OUTFLOW RATES
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Temporal person count accumulation & directional flow rate differential (peds/min)
          </p>
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="h-56 flex flex-col items-center justify-center rounded-xl bg-slate-950/60 border border-slate-800 text-center p-4">
          <p className="text-xs text-slate-400">Waiting for realtime flow telemetry stream...</p>
        </div>
      ) : (
        <div className="h-56 w-full font-mono-nums">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis stroke="#10b981" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#1e293b',
                  borderRadius: '0.75rem',
                  fontSize: '11px',
                }}
                formatter={(val: any, name: any) => {
                  if (name === 'inflow') return [`${val} peds/min`, 'Inflow Rate'];
                  if (name === 'outflow') return [`${val} peds/min`, 'Outflow Rate'];
                  if (name === 'personCount') return [val, 'Person Count'];
                  return [val, name];
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
                formatter={(val) => {
                  if (val === 'inflow') return <span className="text-emerald-400 font-bold">Inflow (/min)</span>;
                  if (val === 'outflow') return <span className="text-amber-400 font-bold">Outflow (/min)</span>;
                  return val;
                }}
              />
              <Bar dataKey="inflow" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="outflow" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
