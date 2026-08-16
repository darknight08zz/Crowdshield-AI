'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { InteractiveMap } from '@/components/dashboard/InteractiveMap';
import { ZoneCardSkeleton, MapSkeleton } from '@/components/ui/Skeleton';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { OperationalWarningBadge, OperationalWarningState } from '@/components/ui/OperationalWarningBadge';
import { CameraHealthBadge, CameraHealthStatus } from '@/components/ui/CameraHealthBadge';
import { ConnectionStatusBadge } from '@/components/ui/ConnectionStatusBadge';
import { ProvenancePanel } from '@/components/ui/ProvenancePanel';
import { api, ZoneData, GateData, RealtimeInferenceResultData } from '@/lib/api';
import { AlertTriangle, Activity, ShieldAlert, CheckCircle2, ChevronRight, Clock, Info } from 'lucide-react';
import Link from 'next/link';
import { useRealtimeInference } from '@/lib/useRealtimeInference';
import { OverviewTemporalSummary } from '@/components/dashboard/OverviewTemporalSummary';
import { AlertHistoryTable } from '@/components/dashboard/AlertHistoryTable';
import { globalTemporalHistoryStore } from '@/lib/temporalHistoryStore';

interface EnrichedZoneData extends ZoneData {
  cameraId?: string;
  cameraHealth?: CameraHealthStatus;
  warningState?: OperationalWarningState;
  physicsRisk?: number;
  aiProbability?: number | null;
  personCount?: number;
  isStale?: boolean;
  telemetryTimestamp?: string;
  densityTrend?: 'UP' | 'DOWN' | 'STABLE';
  speedTrend?: 'UP' | 'DOWN' | 'STABLE';
  inflowTrend?: 'UP' | 'DOWN' | 'STABLE';
  warningReason?: string;
}

export default function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [baseZones, setBaseZones] = useState<ZoneData[]>([]);
  const [gates, setGates] = useState<GateData[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>('');

  // Dictionary of real-time inference payloads per zone ID
  const [realtimeZoneMap, setRealtimeZoneMap] = useState<Record<string, RealtimeInferenceResultData>>({});

  // Active stream subscription based on selected zone
  const activeSub = selectedZoneId
    ? { eventId: 'EVT-MAIN', cameraId: `CAM-${selectedZoneId.substring(0, 6)}`, zoneId: selectedZoneId }
    : null;
  const realtime = useRealtimeInference(activeSub);

  // Sync incoming Phase 6B/6C.1 WebSocket stream payload into zone dictionary
  useEffect(() => {
    if (realtime.data && realtime.data.zone_id) {
      const payload = realtime.data;
      setRealtimeZoneMap((prev) => ({
        ...prev,
        [payload.zone_id]: payload,
      }));
    }
  }, [realtime.data]);

  // Initial REST overview load
  useEffect(() => {
    async function loadData() {
      const data = await api.fetchOverviewData();
      setBaseZones(data.zones || []);
      setGates(data.gates || []);
      if (data.zones && data.zones.length > 0) {
        setSelectedZoneId(data.zones[0].id);
      }
      setLoading(false);
    }
    loadData();
  }, []);

  // Merge static base zones with live stream updates and derive trends
  const zones: EnrichedZoneData[] = useMemo(() => {
    return baseZones.map((z) => {
      const rt = realtimeZoneMap[z.id];
      const cameraId = `CAM-${z.id.substring(0, 6)}`;
      
      if (!rt) {
        return {
          ...z,
          cameraId,
          cameraHealth: 'ONLINE',
          warningState: (z.status === 'CRITICAL SURGE' || z.risk_score >= 80 ? 'HIGH_RISK' : z.risk_score >= 50 ? 'EARLY_WARNING' : 'NORMAL') as OperationalWarningState,
          physicsRisk: z.risk_score,
          aiProbability: null,
          personCount: Math.round((z.current_density || 0) * z.capacity),
          isStale: false,
        };
      }

      const physicsRisk = rt.current_physics_risk ?? rt.current_risk_score ?? z.risk_score;
      const aiProbability = typeof rt.ai_probability === 'number' ? rt.ai_probability : null;
      const warningState = (rt.operational_warning_state || 'NORMAL') as OperationalWarningState;
      const cameraHealth = (rt.camera_health_status || 'ONLINE') as CameraHealthStatus;
      const personCount = rt.telemetry?.person_count ?? Math.round((rt.telemetry?.density || 0) * z.capacity);

      return {
        ...z,
        cameraId,
        current_density: rt.telemetry?.density ?? z.current_density,
        risk_score: physicsRisk,
        physicsRisk,
        aiProbability,
        warningState,
        cameraHealth,
        personCount,
        inflow_rate: rt.telemetry?.inflow_rate ?? z.inflow_rate,
        outflow_rate: rt.telemetry?.outflow_rate ?? z.outflow_rate,
        avg_speed: rt.telemetry?.average_speed ?? z.avg_speed,
        direction_conflict: rt.telemetry?.direction_conflict_score ?? z.direction_conflict,
        isStale: rt.is_stale ?? false,
        telemetryTimestamp: rt.telemetry_timestamp || rt.warning_timestamp,
        warningReason: rt.warning_reason || (warningState === 'HIGH_RISK' ? 'Critical crowd density build-up and outflow bottleneck' : undefined),
      };
    });
  }, [baseZones, realtimeZoneMap]);

  // Operational sorting hierarchy: HIGH_RISK -> EARLY_WARNING -> WATCH -> DEGRADED -> WARMING_UP -> NORMAL
  const sortedZones = useMemo(() => {
    const priorityMap: Record<string, number> = {
      HIGH_RISK: 1,
      EARLY_WARNING: 2,
      WATCH: 3,
      DEGRADED: 4,
      WARMING_UP: 5,
      NORMAL: 6,
    };
    return [...zones].sort((a, b) => {
      const pA = priorityMap[a.warningState || 'NORMAL'] || 99;
      const pB = priorityMap[b.warningState || 'NORMAL'] || 99;
      if (pA !== pB) return pA - pB;
      return (b.physicsRisk || 0) - (a.physicsRisk || 0);
    });
  }, [zones]);

  // Attention-required sectors (HIGH_RISK, EARLY_WARNING, WATCH)
  const attentionZones = useMemo(() => {
    return sortedZones.filter(
      (z) => z.warningState === 'HIGH_RISK' || z.warningState === 'EARLY_WARNING' || z.warningState === 'WATCH'
    );
  }, [sortedZones]);

  // Event summary metrics
  const totalPedestrians = useMemo(() => {
    return zones.reduce((acc, z) => acc + (z.personCount || 0), 0);
  }, [zones]);

  const cameraSummary = useMemo(() => {
    let online = 0, degraded = 0, offline = 0;
    zones.forEach((z) => {
      if (z.cameraHealth === 'OFFLINE') offline++;
      else if (z.cameraHealth === 'DEGRADED') degraded++;
      else online++;
    });
    return { online, degraded, offline, total: zones.length };
  }, [zones]);

  const zoneSummary = useMemo(() => {
    let highRisk = 0, earlyWarning = 0, watch = 0, normal = 0, warmingUp = 0, degraded = 0;
    zones.forEach((z) => {
      if (z.warningState === 'HIGH_RISK') highRisk++;
      else if (z.warningState === 'EARLY_WARNING') earlyWarning++;
      else if (z.warningState === 'WATCH') watch++;
      else if (z.warningState === 'WARMING_UP') warmingUp++;
      else if (z.warningState === 'DEGRADED') degraded++;
      else normal++;
    });
    return { highRisk, earlyWarning, watch, normal, warmingUp, degraded, total: zones.length };
  }, [zones]);

  return (
    <DashboardLayout>
      {/* 1. Header & Live System Status Overview */}
      <div className="card-command p-5 space-y-4 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3 flex-wrap gap-y-1">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
              <h1 className="text-xl font-extrabold text-white tracking-tight">CROWDSHIELD LIVE MONITORING</h1>
              <ConnectionStatusBadge status={realtime.connectionStatus} />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Real-time sector density, physics risk score, and Phase 6B/6C.1 AI early-warning telemetry.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-center">
              <div className="text-[10px] font-bold text-slate-400">TOTAL CROWD ESTIMATE</div>
              <div className="text-lg font-bold text-cyan-400 font-mono-nums">{totalPedestrians.toLocaleString()}</div>
            </div>
            <div className="px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-center">
              <div className="text-[10px] font-bold text-slate-400">CAMERAS</div>
              <div className="text-xs font-extrabold font-mono-nums flex items-center justify-center gap-1.5 mt-0.5">
                <span className="text-emerald-400">{cameraSummary.online} ONLINE</span>
                {cameraSummary.degraded > 0 && <span className="text-amber-400">{cameraSummary.degraded} DEG</span>}
                {cameraSummary.offline > 0 && <span className="text-rose-400">{cameraSummary.offline} OFF</span>}
              </div>
            </div>
            <div className="px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-center">
              <div className="text-[10px] font-bold text-slate-400">SECTORS MONITORED</div>
              <div className="text-xs font-extrabold font-mono-nums flex items-center justify-center gap-1.5 mt-0.5">
                {zoneSummary.highRisk > 0 && <span className="text-rose-400">{zoneSummary.highRisk} HIGH</span>}
                {zoneSummary.earlyWarning > 0 && <span className="text-amber-400">{zoneSummary.earlyWarning} WARN</span>}
                {zoneSummary.watch > 0 && <span className="text-yellow-400">{zoneSummary.watch} WATCH</span>}
                <span className="text-emerald-400">{zoneSummary.normal} SAFE</span>
              </div>
            </div>
          </div>
        </div>

        {/* 2. ATTENTION REQUIRED PANEL */}
        {attentionZones.length > 0 ? (
          <div className="bg-amber-950/40 border border-amber-500/40 p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-amber-300 font-extrabold text-xs tracking-wider uppercase">
                <AlertTriangle className="w-4 h-4 text-amber-400 animate-pulse" />
                <span>ATTENTION REQUIRED ({attentionZones.length} SECTOR{attentionZones.length > 1 ? 'S' : ''})</span>
              </div>
              <span className="text-[10px] text-amber-400/80 font-mono-nums">Prioritized by Operational Policy</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {attentionZones.map((az) => (
                <Link
                  key={az.id}
                  href={`/zones/${az.id}`}
                  className="p-3 rounded-lg bg-slate-950/80 border border-amber-500/30 hover:border-amber-400 transition space-y-2 block"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs font-extrabold text-white">{az.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono-nums">{az.cameraId}</div>
                    </div>
                    <OperationalWarningBadge state={az.warningState} size="sm" />
                  </div>

                  <div className="flex justify-between items-center text-xs border-t border-slate-800/80 pt-2 font-mono-nums">
                    <div>
                      <span className="text-[10px] text-slate-400 block">PHYSICS RISK</span>
                      <span className="font-extrabold text-amber-300">{az.physicsRisk?.toFixed(0)} / 100</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">AI PROBABILITY</span>
                      <span className="font-extrabold text-cyan-300">
                        {az.aiProbability !== null && az.aiProbability !== undefined ? `${(az.aiProbability * 100).toFixed(0)}%` : 'N/A'}
                      </span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-emerald-950/30 border border-emerald-500/30 p-3 rounded-xl flex items-center justify-between text-xs">
            <div className="flex items-center space-x-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-300 font-semibold">
                ALL MONITORED SECTORS OPERATING SAFELY: All crowd density levels and movement speeds within normal thresholds.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 3. Interactive Map & Live Sector Telemetry Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-5">
        {/* Left Column: Map (7 cols) */}
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

          {/* AI Provenance Banner */}
          <ProvenancePanel className="mt-3" />
        </div>

        {/* Right Column: Live Sector Cards Grid (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-cyan-400" />
              SECTOR OPERATOR TELEMETRY GRID
            </h2>
            <span className="text-[10px] text-slate-400 font-mono-nums">
              SORTED BY OPERATIONAL SEVERITY
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3.5 max-h-[640px] overflow-y-auto pr-1">
            {loading
              ? Array(4)
                  .fill(0)
                  .map((_, i) => <ZoneCardSkeleton key={i} />)
              : sortedZones.map((zone) => {
                  const isSelected = selectedZoneId === zone.id;

                  return (
                    <div
                      key={zone.id}
                      onClick={() => setSelectedZoneId(zone.id)}
                      className={`card-command p-4 cursor-pointer risk-transition ${
                        isSelected ? 'border-cyan-400 ring-2 ring-cyan-500/30 shadow-xl bg-slate-900' : ''
                      }`}
                    >
                      {/* Card Header */}
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="font-extrabold text-sm text-white">{zone.name}</h3>
                            <span className="text-[10px] font-mono-nums text-slate-400">({zone.cameraId})</span>
                          </div>
                          <div className="flex items-center space-x-2 mt-1">
                            <CameraHealthBadge status={zone.cameraHealth} />
                            {zone.isStale && (
                              <span className="px-2 py-0.5 text-[9px] font-extrabold rounded bg-amber-950 border border-amber-500/50 text-amber-300 animate-pulse">
                                ⚠ STALE DATA
                              </span>
                            )}
                          </div>
                        </div>

                        <OperationalWarningBadge state={zone.warningState} size="md" />
                      </div>

                      {/* Physics Risk vs AI Probability Indicators */}
                      <div className="grid grid-cols-2 gap-2 mt-3 p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                        <div>
                          <div className="text-[10px] font-bold text-slate-400 uppercase">CURRENT PHYSICS RISK</div>
                          <div className="text-base font-extrabold text-amber-300 font-mono-nums">
                            {zone.physicsRisk !== undefined ? `${zone.physicsRisk.toFixed(0)} / 100` : 'N/A'}
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] font-bold text-slate-400 uppercase">AI EARLY-WARNING</div>
                          {zone.warningState === 'WARMING_UP' ? (
                            <div className="text-xs font-bold text-cyan-300 animate-pulse">AI WARMING UP</div>
                          ) : zone.warningState === 'DEGRADED' || zone.aiProbability === null || zone.aiProbability === undefined ? (
                            <div className="text-xs font-bold text-amber-400">AI UNAVAILABLE</div>
                          ) : (
                            <div className="text-base font-extrabold text-cyan-300 font-mono-nums">
                              {(zone.aiProbability * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Key Live Telemetry Metrics */}
                      <div className="grid grid-cols-4 gap-2 mt-2 text-center text-xs font-mono-nums">
                        <div className="p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
                          <span className="text-[9px] text-slate-400 block">DENSITY</span>
                          <span className="font-bold text-cyan-300">{(zone.current_density || 0).toFixed(1)} p/m²</span>
                        </div>
                        <div className="p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
                          <span className="text-[9px] text-slate-400 block">SPEED</span>
                          <span className="font-bold text-slate-200">{(zone.avg_speed || 0).toFixed(2)} m/s</span>
                        </div>
                        <div className="p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
                          <span className="text-[9px] text-slate-400 block">INFLOW</span>
                          <span className="font-bold text-emerald-400">{zone.inflow_rate ?? 0} /m</span>
                        </div>
                        <div className="p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
                          <span className="text-[9px] text-slate-400 block">OUTFLOW</span>
                          <span className="font-bold text-rose-400">{zone.outflow_rate ?? 0} /m</span>
                        </div>
                      </div>

                      {/* Compact Temporal Trend Summary */}
                      <div className="mt-3">
                        <OverviewTemporalSummary
                          zoneName={zone.name}
                          warningState={zone.warningState || 'NORMAL'}
                          history={globalTemporalHistoryStore.getHistory('EVT-MAIN', zone.cameraId || '', zone.id)}
                        />
                      </div>

                      {/* Card Footer: Freshness & Action Link */}
                      <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between items-center text-xs font-mono-nums">
                        <span className="text-[10px] text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {zone.isStale ? 'Data Stale' : 'Live'}
                        </span>
                        <Link
                          href={`/zones/${zone.id}`}
                          className="text-cyan-400 hover:text-cyan-300 font-extrabold text-[11px] flex items-center gap-1"
                        >
                          OPERATOR ANALYSIS &rarr;
                        </Link>
                      </div>
                    </div>
                  );
                })}
          </div>

          {/* Section: Global Realtime Alert History Log */}
          <div className="pt-4">
            <AlertHistoryTable transitions={globalTemporalHistoryStore.getGlobalTransitions()} />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
