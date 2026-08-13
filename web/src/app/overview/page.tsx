'use client';

import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { InteractiveMap } from '@/components/dashboard/InteractiveMap';
import { ZoneCardSkeleton, MapSkeleton } from '@/components/ui/Skeleton';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { api, ZoneData, GateData } from '@/lib/api';
import { getRiskCategory } from '@/lib/constants';
import { AlertTriangle, Activity } from 'lucide-react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';

export default function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [zones, setZones] = useState<ZoneData[]>([]);
  const [gates, setGates] = useState<GateData[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>('');

  useEffect(() => {
    async function loadData() {
      const data = await api.fetchOverviewData();
      setZones(data.zones || []);
      setGates(data.gates || []);
      if (data.zones && data.zones.length > 0) {
        setSelectedZoneId(data.zones[0].id);
      }
      setLoading(false);
    }
    loadData();

    // Supabase Realtime subscription (CDC without polling)
    const supabase = createClient();
    const channel = supabase
      .channel('realtime:zones')
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'zones' },
        (payload) => {
          setZones((prev) =>
            prev.map((z) => (z.id === payload.new.id ? { ...z, ...payload.new } : z))
          );
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const totalPedestrians = zones.reduce((acc, z) => acc + Math.round((z.current_density || 0) * z.capacity), 0);
  const highestRiskZone = zones.length > 0 
    ? zones.reduce((prev, current) => (prev.risk_score > current.risk_score ? prev : current), zones[0])
    : null;

  return (
    <DashboardLayout>
      {/* 1. Overall Risk Summary Banner */}
      <div className="card-command p-5 space-y-4 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
              <h1 className="text-xl font-extrabold text-white tracking-tight">CONTROL ROOM COMMAND OVERVIEW</h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Live venue crowd mechanics, physical choke-point telemetry, and automated AI risk monitoring.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-center">
              <div className="text-[10px] font-bold text-slate-400">TOTAL CROWD ESTIMATE</div>
              <div className="text-lg font-bold text-cyan-400 font-mono-nums">{totalPedestrians.toLocaleString()}</div>
            </div>
            <div className="px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-center flex flex-col items-center justify-center">
              <div className="text-[10px] font-bold text-slate-400 mb-0.5">HIGHEST ZONE RISK</div>
              <RiskBadge score={highestRiskZone?.risk_score ?? 0} size="sm" />
            </div>
          </div>
        </div>

        {/* Global Alert Bar */}
        {highestRiskZone && highestRiskZone.name && (highestRiskZone.risk_score >= 50 || highestRiskZone.status === 'CRITICAL SURGE' || highestRiskZone.status === 'HIGH') ? (
          <div className="bg-rose-950/40 border border-rose-500/40 p-3 rounded-xl flex items-center justify-between text-xs risk-transition">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 animate-pulse" />
              <div>
                <span className="font-bold text-rose-300">ACTIVE {highestRiskZone.status || 'SURGE'} DETECTED: </span>
                <span className="text-slate-300">
                  {highestRiskZone.name} at {Math.round((highestRiskZone.current_density || 0) * 100)}% capacity. Action recommended.
                </span>
              </div>
            </div>
            <Link
              href={`/zones/${highestRiskZone.id}`}
              className="btn-danger text-xs py-1.5 px-3"
            >
              DISPATCH AI ACTION &rarr;
            </Link>
          </div>
        ) : (
          <div className="bg-emerald-950/30 border border-emerald-500/30 p-3 rounded-xl flex items-center justify-between text-xs">
            <div className="flex items-center space-x-3">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-emerald-300 font-semibold">
                SYSTEM STATUS NORMAL: All monitored sectors operating within safe capacity limits.
              </span>
            </div>
          </div>
        )}
      </div>


      {/* 2. Interactive Map & Zone Telemetry Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-5">
        {/* Left Column: Interactive Vector / Leaflet Overlay Map (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          {loading ? (
            <MapSkeleton />
          ) : (
            <InteractiveMap
              zones={zones}
              gates={gates}
              selectedZoneId={selectedZoneId}
              onSelectZone={(id) => setSelectedZoneId(id)}
            />
          )}
        </div>

        {/* Right Column: Live Zone Cards Grid (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-cyan-400" />
              LIVE SECTOR TELEMETRY GRID
            </h2>
            <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30 font-mono-nums">
              REALTIME CDC ACTIVE
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 max-h-[520px] overflow-y-auto pr-1">
            {loading
              ? Array(4)
                  .fill(0)
                  .map((_, i) => <ZoneCardSkeleton key={i} />)
              : zones.map((zone) => {
                  const isSelected = selectedZoneId === zone.id;

                  return (
                    <div
                      key={zone.id}
                      onClick={() => setSelectedZoneId(zone.id)}
                      className={`card-command p-4 cursor-pointer risk-transition ${
                        isSelected ? 'border-cyan-400 ring-2 ring-cyan-500/30 shadow-xl bg-slate-900' : ''
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-extrabold text-sm text-white">{zone.name}</h3>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            Capacity: <strong className="text-slate-200 font-mono-nums">{zone.capacity.toLocaleString()}</strong> | Density: <strong className="text-cyan-300 font-mono-nums">{Math.round((zone.current_density || 0) * 100)}%</strong>
                          </div>
                        </div>

                        <RiskBadge score={zone.risk_score} size="md" />
                      </div>

                      {/* Density Bar */}
                      <div className="mt-3 space-y-1">
                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="h-full transition-all duration-300 rounded-full bg-cyan-500"
                            style={{
                              width: `${Math.min(100, (zone.current_density || 0) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>

                      {/* Quick Action Footer */}
                      <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between items-center text-xs">
                        <span className="text-[11px] text-slate-400 flex items-center gap-1">
                          Inflow: <strong className="text-slate-200 font-mono-nums">{zone.inflow_rate ?? 0} p/m</strong>
                        </span>
                        <Link
                          href={`/zones/${zone.id}`}
                          className="text-cyan-400 hover:text-cyan-300 font-bold text-[11px] flex items-center gap-1"
                        >
                          Inspect Sector &rarr;
                        </Link>
                      </div>
                    </div>
                  );
                })}
          </div>
        </div>
      </div>

    </DashboardLayout>
  );
}
