'use client';

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Clock, 
  AlertTriangle, 
  ShieldCheck, 
  Download, 
  RefreshCw, 
  Layers, 
  Zap, 
  Activity, 
  CheckCircle2,
  FileText
} from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { api, ZoneData } from '@/lib/api';

export default function AnalyticsPage() {
  const [selectedZoneId, setSelectedZoneId] = useState<string>('all');
  const [timeWindowHours, setTimeWindowHours] = useState<number>(1);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);

  const [zones, setZones] = useState<ZoneData[]>([]);
  const [trendsData, setTrendsData] = useState<any>(null);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);
  const [reportData, setReportData] = useState<any>(null);

  const [eventId, setEventId] = useState<string>('');

  // Fetch data
  const loadData = async () => {
    try {
      setLoading(true);
      const overview = await api.fetchOverviewData();
      setZones(overview.zones || []);

      let activeEventId = overview.event?.id;
      if (!activeEventId || !api.isValidUUID(activeEventId)) {
        const events = await api.fetchEvents();
        if (events && events.length > 0) {
          activeEventId = events[0].id;
        }
      }

      if (activeEventId && api.isValidUUID(activeEventId)) {
        setEventId(activeEventId);
        const trends = await api.fetchZoneTrends(
          activeEventId, 
          selectedZoneId === 'all' ? undefined : selectedZoneId, 
          timeWindowHours
        );
        setTrendsData(trends);

        const summary = await api.fetchEventAnalyticsSummary(activeEventId);
        setSummaryData(summary);
      }
    } catch (e) {
      console.error('Failed to load analytics data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedZoneId, timeWindowHours]);

  // Auto-refresh interval (default 1-hour live updating)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadData();
    }, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedZoneId, timeWindowHours]);

  const handleExportReport = async () => {
    if (!eventId || !api.isValidUUID(eventId)) return;
    try {
      const rData = await api.exportPostEventReport(eventId);
      setReportData(rData);
      setReportModalOpen(true);
    } catch (e) {
      console.error('Failed to export post-event report:', e);
    }
  };


  const snapshots = trendsData?.snapshots || [];
  const derived = trendsData?.derived_stats || {};

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />

        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top Title & Controls Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 shadow-lg">
            <div>
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    Crowd Trend Analytics & Predictive History
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      LIVE STREAM
                    </span>
                  </h1>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Historical density curves, risk trajectories, and event-wide intervention efficacy benchmark metrics.
                  </p>
                </div>
              </div>
            </div>

            {/* Time Window & Filter Toolbar */}
            <div className="flex items-center flex-wrap gap-3">
              {/* Zone Filter */}
              <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                <Layers className="w-4 h-4 text-slate-400" />
                <select
                  value={selectedZoneId}
                  onChange={(e) => setSelectedZoneId(e.target.value)}
                  className="bg-transparent text-xs text-slate-200 font-semibold focus:outline-none cursor-pointer"
                >
                  <option value="all" className="bg-slate-900 text-slate-200">All Sectors (Event Summary)</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id} className="bg-slate-900 text-slate-200">
                      {z.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Time Horizon Preset Toggle */}
              <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                {[
                  { label: 'Last 1h', hours: 1 },
                  { label: 'Last 3h', hours: 3 },
                  { label: 'Last 6h', hours: 6 },
                  { label: '24h', hours: 24 },
                ].map((preset) => (
                  <button
                    key={preset.hours}
                    onClick={() => setTimeWindowHours(preset.hours)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                      timeWindowHours === preset.hours
                        ? 'bg-purple-500 text-white shadow-md shadow-purple-950'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              {/* Auto Refresh Toggle */}
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`p-2 rounded-xl border transition ${
                  autoRefresh
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                    : 'bg-slate-900 text-slate-400 border-slate-800'
                }`}
                title={autoRefresh ? 'Auto-refresh active (15s)' : 'Auto-refresh paused'}
              >
                <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
              </button>

              {/* Executive Report Export */}
              <button
                onClick={handleExportReport}
                className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-950 transition"
              >
                <Download className="w-4 h-4" />
                <span>Export Post-Event Report</span>
              </button>
            </div>
          </div>

          {/* Derived Statistics Summary Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80 shadow-md">
              <div className="flex items-center justify-between text-xs font-bold text-slate-400">
                <span>PEAK RISK SCORE</span>
                <AlertTriangle className="w-4 h-4 text-rose-400" />
              </div>
              <div className="text-2xl font-black text-rose-400 mt-2">
                {derived.peak_risk_score ?? '--'}/100
              </div>
              <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Peak at {derived.peak_risk_timestamp ? new Date(derived.peak_risk_timestamp).toLocaleTimeString() : 'N/A'}</span>
              </div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80 shadow-md">
              <div className="flex items-center justify-between text-xs font-bold text-slate-400">
                <span>SUSTAINED CRITICAL DURATION</span>
                <Clock className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-black text-amber-400 mt-2">
                {derived.sustained_critical_minutes ?? 0} <span className="text-xs font-normal text-slate-400">mins</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Total duration in CRITICAL (≥75) status
              </div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80 shadow-md">
              <div className="flex items-center justify-between text-xs font-bold text-slate-400">
                <span>SURGE ESCALATIONS</span>
                <Zap className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-black text-purple-400 mt-2">
                {derived.escalation_count ?? 0} <span className="text-xs font-normal text-slate-400">events</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Distinct transitions to HIGH / CRITICAL
              </div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80 shadow-md">
              <div className="flex items-center justify-between text-xs font-bold text-slate-400">
                <span>AVERAGE SECTOR RISK</span>
                <Activity className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-black text-cyan-400 mt-2">
                {derived.average_risk_score ?? '--'}/100
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Mean across window (Window: {timeWindowHours}h)
              </div>
            </div>
          </div>

          {/* Time-Series Charts Section */}
          <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Time-Series Risk Score & Crowd Density Velocity Trajectory
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Showing snapshots recorded over the last {timeWindowHours} hour(s) for {selectedZoneId === 'all' ? 'All Monitored Sectors' : 'Selected Sector'}.
                </p>
              </div>

              {/* Legend Badges */}
              <div className="flex items-center space-x-4 text-xs font-semibold">
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-full bg-rose-500"></span>
                  <span className="text-slate-300">Risk Score</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-full bg-cyan-400"></span>
                  <span className="text-slate-300">Density %</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-full bg-emerald-400"></span>
                  <span className="text-slate-300">Inflow Speed</span>
                </div>
              </div>
            </div>

            {/* SVG Interactive Time-Series Chart */}
            <div className="w-full h-64 bg-slate-950/80 rounded-xl p-4 border border-slate-800/80 relative flex flex-col justify-between">
              {snapshots.length === 0 ? (
                <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
                  Loading time-series snapshot stream...
                </div>
              ) : (
                <svg className="w-full h-full overflow-visible" viewBox="0 0 800 200" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  <line x1="0" y1="40" x2="800" y2="40" stroke="#334155" strokeDasharray="3 3" strokeWidth="1" />
                  <line x1="0" y1="100" x2="800" y2="100" stroke="#334155" strokeDasharray="3 3" strokeWidth="1" />
                  <line x1="0" y1="160" x2="800" y2="160" stroke="#334155" strokeDasharray="3 3" strokeWidth="1" />

                  {/* Threshold Line (Critical = 75) */}
                  <line x1="0" y1="50" x2="800" y2="50" stroke="#f43f5e" strokeDasharray="4 4" strokeWidth="1.5" opacity="0.6" />

                  {/* Risk Score Path (Crimson Line) */}
                  {snapshots.length > 1 && (
                    <polyline
                      fill="none"
                      stroke="#f43f5e"
                      strokeWidth="3"
                      points={snapshots.map((s: any, idx: number) => {
                        const x = (idx / (snapshots.length - 1)) * 800;
                        const y = 200 - (s.risk_score / 100) * 180;
                        return `${x},${y}`;
                      }).join(' ')}
                    />
                  )}

                  {/* Density % Path (Cyan Line) */}
                  {snapshots.length > 1 && (
                    <polyline
                      fill="none"
                      stroke="#22d3ee"
                      strokeWidth="2.5"
                      strokeDasharray="2 2"
                      points={snapshots.map((s: any, idx: number) => {
                        const x = (idx / (snapshots.length - 1)) * 800;
                        const y = 200 - (s.density_pct / 100) * 180;
                        return `${x},${y}`;
                      }).join(' ')}
                    />
                  )}

                  {/* Data Points */}
                  {snapshots.map((s: any, idx: number) => {
                    const x = (idx / (snapshots.length - 1)) * 800;
                    const yRisk = 200 - (s.risk_score / 100) * 180;
                    return (
                      <g key={s.id || idx}>
                        <circle cx={x} cy={yRisk} r="4" fill="#f43f5e" className="hover:r-6 transition" />
                      </g>
                    );
                  })}
                </svg>
              )}

              {/* Time X-Axis Labels */}
              <div className="flex justify-between text-[10px] font-semibold text-slate-500 pt-2 border-t border-slate-800/80">
                {snapshots.filter((_: any, i: number) => i % Math.max(1, Math.floor(snapshots.length / 6)) === 0).map((s: any) => (
                  <span key={s.timestamp}>{new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Event-Wide Analytics Summary & Intervention Effectiveness */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Elevated Risk Sectors Ranking */}
            <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 shadow-lg space-y-4">
              <h3 className="text-sm font-bold text-slate-200 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  Sectors Ranked by Elevated Risk Duration
                </span>
                <span className="text-xs font-normal text-slate-400">Total Monitored: {summaryData?.total_monitored_zones ?? 4}</span>
              </h3>

              <div className="space-y-2.5">
                {(summaryData?.zones_ranked_by_elevated_risk || []).map((z: any, idx: number) => (
                  <div key={z.zone_id} className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-3">
                      <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-bold text-[10px]">
                        #{idx + 1}
                      </span>
                      <div>
                        <div className="font-bold text-slate-200">{z.zone_name}</div>
                        <div className="text-[10px] text-slate-500">Cap: {z.capacity} peds | Peak Risk: {z.peak_risk_score}/100</div>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="font-bold text-amber-400">{z.elevated_risk_minutes} mins</div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        {z.risk_bucket}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Intervention Effectiveness Benchmark */}
            <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 shadow-lg space-y-4">
              <h3 className="text-sm font-bold text-slate-200 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Intervention Efficacy Benchmark
                </span>
                <span className="text-xs font-bold text-emerald-400 bg-emerald-500/20 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
                  {summaryData?.intervention_success_rate_pct ?? 100}% Success Rate
                </span>
              </h3>

              <div className="space-y-2.5">
                {(summaryData?.intervention_effectiveness || []).map((item: any, idx: number) => (
                  <div key={item.recommendation_id || idx} className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-200">{item.action_title}</span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        -{item.risk_reduction_points} PTS ({item.risk_reduction_pct}%)
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 bg-slate-900/70 p-2 rounded-lg">
                      <div>
                        Initial Risk: <span className="font-bold text-rose-400">{item.before_risk_score}</span>
                      </div>
                      <div>→</div>
                      <div>
                        Post Risk: <span className="font-bold text-emerald-400">{item.after_risk_score}</span>
                      </div>
                      <div className="text-slate-500 text-[10px]">
                        {new Date(item.approved_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Exportable Executive Post-Event Report Modal */}
      {reportModalOpen && reportData && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-6 shadow-2xl overflow-y-auto max-h-[90vh]">
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-3 bg-purple-500/20 text-purple-400 rounded-xl border border-purple-500/30">
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-100">{reportData.title}</h2>
                  <p className="text-xs text-slate-400">Generated on {new Date(reportData.generated_at).toLocaleString()}</p>
                </div>
              </div>
              <button
                onClick={() => setReportModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold px-3 py-1 rounded-lg bg-slate-800"
              >
                ✕ Close
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-4 bg-purple-950/30 border border-purple-500/30 rounded-xl space-y-1">
                <div className="font-bold text-purple-300 uppercase tracking-wider text-[10px]">Prepared For</div>
                <div className="text-slate-200 font-semibold">{reportData.prepared_for}</div>
              </div>

              <div className="space-y-2">
                <div className="font-bold text-slate-300 uppercase tracking-wider text-[10px]">Executive Summary</div>
                <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                  {reportData.executive_summary}
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(reportData.key_metrics || {}).map(([key, val]: any) => (
                  <div key={key} className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-center">
                    <div className="text-[10px] font-bold text-slate-500 uppercase">{key.replace(/_/g, ' ')}</div>
                    <div className="text-sm font-black text-cyan-400 mt-1">{val}</div>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="font-bold text-slate-300 uppercase tracking-wider text-[10px]">Official Security Audit Verdict</div>
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 rounded-xl font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  {reportData.key_metrics?.safety_verdict}
                </div>
              </div>

              <div className="text-[10px] text-slate-500 pt-2 border-t border-slate-800 italic">
                {reportData.disclaimer}
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
              <button
                onClick={() => window.print()}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold flex items-center space-x-2"
              >
                <Download className="w-4 h-4" />
                <span>Print / Save PDF</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
