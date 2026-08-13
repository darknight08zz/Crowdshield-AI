'use client';

import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Skeleton } from '@/components/ui/Skeleton';
import { api, OfficerData } from '@/lib/api';
import { Users, BatteryCharging, Radio, MapPin } from 'lucide-react';

export default function OfficersPage() {
  const [loading, setLoading] = useState(true);
  const [officers, setOfficers] = useState<OfficerData[]>([]);

  useEffect(() => {
    async function loadOfficers() {
      const data = await api.fetchOfficers();
      setOfficers(data);
      setLoading(false);
    }
    loadOfficers();
  }, []);

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Users className="w-5 h-5 text-cyan-400" />
            FIELD OFFICER ROSTER & GROUND RESOURCES
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time situational awareness of deployed security personnel and task completion status.
          </p>
        </div>

        <div className="flex items-center space-x-3 bg-slate-900 px-4 py-2 rounded-xl border border-slate-800 text-xs font-mono-nums">
          <div className="text-slate-400">ACTIVE DEPLOYED SQUADS: <strong className="text-cyan-400 font-bold">{officers.length} OFFICERS</strong></div>
        </div>
      </div>

      {/* Officers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
        {loading
          ? Array(4)
              .fill(0)
              .map((_, i) => <Skeleton key={i} className="h-48 w-full rounded-2xl" />)
          : officers.map((off) => (
              <div
                key={off.id}
                className="card-command p-5 space-y-4 shadow-xl hover:border-slate-700 transition"
              >
                {/* Top Info */}
                <div className="flex justify-between items-start">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 flex items-center justify-center font-black text-sm">
                      {off.name.split(' ').map((n) => n[0]).join('')}
                    </div>
                    <div>
                      <h3 className="font-extrabold text-sm text-white">{off.name}</h3>
                      <div className="text-[10px] text-slate-400 font-mono-nums">{off.badge_number}</div>
                    </div>
                  </div>

                  <span
                    className={`px-2.5 py-0.5 text-[10px] font-black rounded-full uppercase border ${
                      off.status === 'in_progress'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        : off.status === 'completed'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                        : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                    }`}
                  >
                    {off.status.replace('_', ' ')}
                  </span>
                </div>

                {/* Assigned Sector & Active Directive */}
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1 text-xs">
                  <div className="text-[10px] font-bold text-slate-500 flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-cyan-400" />
                    ASSIGNED SECTOR:
                  </div>
                  <div className="font-bold text-cyan-300 text-[11px]">{off.assigned_zone_name}</div>
                  <div className="pt-2 text-slate-300 text-[11px] leading-snug">
                    <strong className="text-slate-400">Task: </strong>{off.current_task}
                  </div>
                </div>

                {/* Telemetry Footer */}
                <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-800/60 font-mono-nums">
                  <span className="flex items-center gap-1">
                    <BatteryCharging className="w-3.5 h-3.5 text-emerald-400" />
                    Battery: {off.battery_level}%
                  </span>
                  <span className="flex items-center gap-1">
                    <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                    Ping: {off.last_ping}
                  </span>
                </div>
              </div>
            ))}
      </div>
    </DashboardLayout>
  );
}
