'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Skeleton } from '@/components/ui/Skeleton';
import { api } from '@/lib/api';
import { useAuth } from '@/components/providers/AuthProvider';
import { IncidentCanonicalData, CanonicalIncidentStatus } from '@/types/incident';
import { IncidentCard } from '@/components/incidents/IncidentCard';
import { IncidentDetailDrawer } from '@/components/incidents/IncidentDetailDrawer';
import { IncidentStatusBadge } from '@/components/incidents/IncidentStatusBadge';
import { IncidentSeverityBadge } from '@/components/incidents/IncidentSeverityBadge';
import {
  AlertTriangle,
  Filter,
  CheckCircle2,
  RefreshCw,
  Radio,
  Flame,
  ShieldCheck,
  Search,
  AlertCircle,
  Eye,
  ShieldAlert,
} from 'lucide-react';

export default function IncidentCenterPage() {
  const { accessToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<IncidentCanonicalData[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedIncident, setSelectedIncident] = useState<IncidentCanonicalData | null>(null);

  // Fetch canonical incidents from backend API
  const loadIncidents = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setErrorMsg(null);
      const data = await api.fetchCanonicalIncidents({}, accessToken || undefined);
      setIncidents(data || []);

      // If selected incident is currently open, refresh its detail
      if (selectedIncident) {
        const updated = data.find((i) => i.incident_id === selectedIncident.incident_id);
        if (updated) {
          setSelectedIncident(updated);
        }
      }
    } catch (e: any) {
      console.error('Error fetching canonical incidents:', e);
      setErrorMsg(e.message || 'Failed to load canonical incidents from backend.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [accessToken, selectedIncident]);

  useEffect(() => {
    loadIncidents(true);
    // Realtime background poll every 10 seconds to sync state with backend
    const interval = setInterval(() => {
      loadIncidents(false);
    }, 10000);
    return () => clearInterval(interval);
  }, [loadIncidents]);

  const handleManualRefresh = () => {
    setRefreshing(true);
    loadIncidents(false);
  };

  // Transition handler
  const handleTransitionExecute = async (
    targetStatus: CanonicalIncidentStatus,
    reason: string
  ) => {
    if (!selectedIncident) return;
    try {
      const updated = await api.transitionIncidentStatus(
        selectedIncident.incident_id,
        { new_status: targetStatus, reason },
        accessToken || undefined
      );

      // Update local state authoritatively
      setIncidents((prev) =>
        prev.map((inc) => (inc.incident_id === updated.incident_id ? updated : inc))
      );
      setSelectedIncident(updated);
    } catch (err: any) {
      console.error('Transition error:', err);
      // Re-throw to be caught and displayed by the confirmation dialog
      throw err;
    }
  };

  // Incident Prioritization (Part 5):
  // 1. HIGH_RISK > EARLY_WARNING > WATCH > DEGRADED > NORMAL
  // 2. OPEN > ACKNOWLEDGED > INVESTIGATING > MITIGATING > RESOLVED / FALSE_POSITIVE
  const warningPriority: Record<string, number> = {
    HIGH_RISK: 5,
    EARLY_WARNING: 4,
    WATCH: 3,
    DEGRADED: 2,
    WARMING_UP: 1,
    NORMAL: 0,
  };

  const statusPriority: Record<string, number> = {
    OPEN: 5,
    ACKNOWLEDGED: 4,
    INVESTIGATING: 3,
    MITIGATING: 2,
    RESOLVED: 1,
    FALSE_POSITIVE: 0,
  };

  const sortedIncidents = [...incidents].sort((a, b) => {
    const aWarn = a.latest_snapshot?.latest_warning_state || a.creation_snapshot?.warning_state_at_creation || 'NORMAL';
    const bWarn = b.latest_snapshot?.latest_warning_state || b.creation_snapshot?.warning_state_at_creation || 'NORMAL';

    const pWarnA = warningPriority[aWarn] ?? 0;
    const pWarnB = warningPriority[bWarn] ?? 0;
    if (pWarnA !== pWarnB) return pWarnB - pWarnA;

    const pStatA = statusPriority[a.status] ?? 0;
    const pStatB = statusPriority[b.status] ?? 0;
    if (pStatA !== pStatB) return pStatB - pStatA;

    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const filteredIncidents = sortedIncidents.filter((inc) => {
    const matchesStatus = statusFilter === 'ALL' || inc.status === statusFilter;
    const q = searchQuery.toLowerCase().trim();
    const matchesQuery =
      !q ||
      inc.incident_id.toLowerCase().includes(q) ||
      inc.zone_id.toLowerCase().includes(q) ||
      (inc.camera_id && inc.camera_id.toLowerCase().includes(q)) ||
      inc.event_id.toLowerCase().includes(q);
    return matchesStatus && matchesQuery;
  });

  // Metrics summary counts
  const activeCount = incidents.filter((i) => !['RESOLVED', 'FALSE_POSITIVE'].includes(i.status)).length;
  const highRiskCount = incidents.filter(
    (i) => (i.latest_snapshot?.latest_warning_state || i.creation_snapshot?.warning_state_at_creation) === 'HIGH_RISK'
  ).length;
  const earlyWarningCount = incidents.filter(
    (i) => (i.latest_snapshot?.latest_warning_state || i.creation_snapshot?.warning_state_at_creation) === 'EARLY_WARNING'
  ).length;
  const investigatingCount = incidents.filter((i) => i.status === 'INVESTIGATING').length;
  const mitigatingCount = incidents.filter((i) => i.status === 'MITIGATING').length;

  return (
    <DashboardLayout>
      <div className="space-y-5">
        {/* Command Header (Part 3) */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
                  OPERATOR INCIDENT ACTION CENTER
                </h1>
                <p className="text-xs text-slate-400 mt-0.5 font-sans">
                  Real-time operational incident command, state-machine triage &amp; immutable audit ledger.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono-nums">
              <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
              <span className="text-emerald-400 font-bold">REALTIME STREAM: LIVE</span>
            </div>

            <button
              onClick={handleManualRefresh}
              disabled={refreshing}
              className="btn-secondary py-2 px-3 text-xs inline-flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Command Center Summary Metrics Ribbon */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex justify-between items-center">
            <div>
              <div className="text-[10px] font-bold text-slate-500 uppercase">ACTIVE INCIDENTS</div>
              <div className="text-lg font-black text-white font-mono-nums">{activeCount}</div>
            </div>
            <AlertCircle className="w-5 h-5 text-rose-400" />
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex justify-between items-center">
            <div>
              <div className="text-[10px] font-bold text-slate-500 uppercase">HIGH RISK</div>
              <div className="text-lg font-black text-rose-400 font-mono-nums">{highRiskCount}</div>
            </div>
            <Flame className="w-5 h-5 text-rose-500" />
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex justify-between items-center">
            <div>
              <div className="text-[10px] font-bold text-slate-500 uppercase">EARLY WARNING</div>
              <div className="text-lg font-black text-amber-400 font-mono-nums">{earlyWarningCount}</div>
            </div>
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex justify-between items-center">
            <div>
              <div className="text-[10px] font-bold text-slate-500 uppercase">INVESTIGATING</div>
              <div className="text-lg font-black text-cyan-400 font-mono-nums">{investigatingCount}</div>
            </div>
            <Eye className="w-5 h-5 text-cyan-400" />
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex justify-between items-center">
            <div>
              <div className="text-[10px] font-bold text-slate-500 uppercase">MITIGATING</div>
              <div className="text-lg font-black text-purple-400 font-mono-nums">{mitigatingCount}</div>
            </div>
            <ShieldAlert className="w-5 h-5 text-purple-400" />
          </div>
        </div>

        {/* Filter Controls (Part 3) */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-2xl bg-slate-950 border border-slate-800 text-xs">
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
            <Filter className="w-4 h-4 text-slate-500 ml-1 shrink-0" />
            {['ALL', 'OPEN', 'ACKNOWLEDGED', 'INVESTIGATING', 'MITIGATING', 'RESOLVED', 'FALSE_POSITIVE'].map(
              (st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1.5 rounded-xl font-bold uppercase transition shrink-0 ${
                    statusFilter === st
                      ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-950/50'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              )
            )}
          </div>

          <div className="relative min-w-[200px]">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, Zone, Camera..."
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 text-xs"
            />
          </div>
        </div>

        {/* Error Banner */}
        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/50 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Main Workspace Layout (Grid / Detail Panel split) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Incidents List Grid */}
          <div className={selectedIncident ? 'lg:col-span-6' : 'lg:col-span-12'}>
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {Array(6)
                  .fill(0)
                  .map((_, i) => (
                    <div key={i} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
                      <Skeleton className="h-6 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-12 w-full" />
                    </div>
                  ))}
              </div>
            ) : filteredIncidents.length === 0 ? (
              /* Empty State (Part 20) */
              <div className="p-12 rounded-2xl bg-slate-950 border border-slate-800 text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <h3 className="text-base font-extrabold text-white">ALL CLEAR</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto font-sans">
                  No active incidents require operator action for status filter &ldquo;{statusFilter}&rdquo;. Realtime CCTV telemetry stream is continuously monitoring.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4">
                {filteredIncidents.map((inc) => (
                  <IncidentCard
                    key={inc.incident_id}
                    incident={inc}
                    isSelected={selectedIncident?.incident_id === inc.incident_id}
                    onSelect={(selected) => setSelectedIncident(selected)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Incident Detail Drawer (Part 6) */}
          {selectedIncident && (
            <div className="lg:col-span-6">
              <IncidentDetailDrawer
                incident={selectedIncident}
                onClose={() => setSelectedIncident(null)}
                onTransitionSuccess={(updated) => {
                  setIncidents((prev) =>
                    prev.map((inc) => (inc.incident_id === updated.incident_id ? updated : inc))
                  );
                  setSelectedIncident(updated);
                }}
                onTransitionExecute={handleTransitionExecute}
              />
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
