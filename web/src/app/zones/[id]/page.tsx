'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Skeleton } from '@/components/ui/Skeleton';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { api, RecommendationData } from '@/lib/api';
import { BEHAVIOR_COLORS } from '@/lib/constants';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Edit3,
  Play,
  TrendingUp,
  Zap,
  Shield,
  Volume2,
} from 'lucide-react';
import Link from 'next/link';

export default function ZoneDetailPage() {
  const params = useParams();
  const router = useRouter();
  const zoneId = (params?.id as string) || 'z-1';

  const [loading, setLoading] = useState(true);
  const [riskData, setRiskData] = useState<any>(null);
  const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);

  // Language & Announcement State
  const [selectedLang, setSelectedLang] = useState<'en' | 'hi'>('en');
  const [draftedAnnouncement, setDraftedAnnouncement] = useState<string>('');
  const [originalDraft, setOriginalDraft] = useState<string>('');

  // Simulation State
  const [simulating, setSimulating] = useState(false);
  const [proposedAction, setProposedAction] = useState<string>(
    'ENFORCE_ONE_WAY_FLOW: Deploy directional barriers and staff near route route-aa111111'
  );
  const [simResult, setSimResult] = useState<any>(null);

  // Decision Modal Confirmation
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingDecision, setPendingDecision] = useState<'approved' | 'rejected' | 'modified'>('approved');
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);

  // Load Zone Risk & Recommendation (Language Aware)
  useEffect(() => {
    async function loadDetail() {
      let targetZoneId = (params?.id as string);
      if (!targetZoneId || !api.isValidUUID(targetZoneId)) {
        const overview = await api.fetchOverviewData();
        if (overview.zones && overview.zones.length > 0) {
          targetZoneId = overview.zones[0].id;
        }
      }

      if (targetZoneId && api.isValidUUID(targetZoneId)) {
        const [rData, recData] = await Promise.all([
          api.fetchZoneRisk(targetZoneId),
          api.fetchZoneRecommendation(targetZoneId, selectedLang),
        ]);
        setRiskData(rData);
        setRecommendation(recData);

        if (recData?.drafted_announcement) {
          setDraftedAnnouncement(recData.drafted_announcement);
          setOriginalDraft(recData.drafted_announcement);
        }
      }
      setLoading(false);
    }
    loadDetail();
  }, [params?.id, selectedLang]);


  const handleSimulate = async () => {
    setSimulating(true);
    const res = await api.simulateIntervention(zoneId, proposedAction);
    setSimResult(res);
    setSimulating(false);
  };

  const handleConfirmDecision = async () => {
    if (!recommendation) return;
    setLoading(true);
    const res = await api.decideRecommendation(
      recommendation.id,
      pendingDecision,
      proposedAction,
      draftedAnnouncement,
      originalDraft
    );
    setShowConfirmModal(false);
    setDecisionSuccess(res.message);
    setLoading(false);

    // Redirect to verify page after 2 seconds
    setTimeout(() => {
      router.push('/verify');
    }, 2000);
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array(4)
              .fill(0)
              .map((_, i) => (
                <Skeleton key={i} className="h-28 w-full" />
              ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </DashboardLayout>
    );
  }

  const behaviorKey = riskData?.behavior_classification || recommendation?.behavior_classification || 'REVERSE_FLOW';
  const behaviorConfig = BEHAVIOR_COLORS[behaviorKey] || BEHAVIOR_COLORS.REVERSE_FLOW;

  const selectableActions = [
    {
      action_type: 'ENFORCE_ONE_WAY_FLOW',
      title: 'Enforce One-Way Route',
      description: 'ENFORCE_ONE_WAY_FLOW: Deploy directional barriers and staff near designated routes to eliminate counter-flow.',
    },
    {
      action_type: 'OPEN_EMERGENCY_GATE',
      title: 'Open Emergency Gate',
      description: 'UNLOCK Emergency Gate 1 & DISPATCH Officer Squad to re-route crowd towards exit promenade.',
    },
    {
      action_type: 'RESTRICT_ENTRY_GATE',
      title: 'Restrict Entry Gate',
      description: 'RESTRICT_GATE: Meter entry rate at Gate 2 by 50% to prevent sector over-crowding.',
    },
    {
      action_type: 'DISPATCH_FIELD_OFFICERS',
      title: 'Dispatch Officer Squad',
      description: 'DISPATCH_FIELD_OFFICERS: Deploy 4 field officers to clear bottlenecks and assist movement.',
    },
    {
      action_type: 'ISSUE_PUBLIC_ANNOUNCEMENT',
      title: 'Broadcast Announcement',
      description: 'ISSUE_PUBLIC_ANNOUNCEMENT: Broadcast public address advisory and send push alerts to citizen devices.',
    },
  ];

  return (
    <DashboardLayout>
      {/* Top Header & Navigation */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/overview"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
              SECTOR ANALYSIS: <span className="text-cyan-400">{recommendation?.zone_name || riskData?.zone_name || `Sector (${zoneId.substring(0, 6)})`}</span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Zone ID: <code className="text-slate-300 font-mono-nums">{zoneId}</code> | Deep Learning Feature Vector & Explainable AI
            </p>
          </div>
        </div>

        {/* Labeled Badges: Shared Standardized RiskBadge + Behavior Badge + Panic Propagation Source Badge */}
        <div className="flex items-center gap-2.5">
          <RiskBadge score={riskData?.current_risk_score ?? riskData?.risk_score ?? 0} size="lg" />

          <span className={`px-3.5 py-1.5 text-xs font-black rounded-lg border ${behaviorConfig.badge}`}>
            BEHAVIOR: {behaviorConfig.label}
          </span>

          {/* Panic Propagation Risk Source Badge */}
          <span
            className={`px-3 py-1.5 text-xs font-black rounded-lg border uppercase tracking-wider ${
              riskData?.risk_source?.startsWith('propagated_from')
                ? 'bg-purple-950/80 border-purple-500/60 text-purple-300 shadow-sm'
                : 'bg-emerald-950/80 border-emerald-500/60 text-emerald-300'
            }`}
          >
            SOURCE: {riskData?.risk_source?.startsWith('propagated_from')
              ? `PROPAGATED FROM ${riskData?.propagated_from_zone_name || 'NEIGHBOR'}`
              : 'INDEPENDENT'}
          </span>
        </div>
      </div>

      {decisionSuccess && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-500/50 rounded-xl text-emerald-300 font-semibold text-xs flex items-center justify-between mt-4">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            {decisionSuccess}
          </span>
          <span className="text-xs text-slate-400">Redirecting to Verification Loop &rarr;</span>
        </div>
      )}

      {/* 1. Risk Trend & Multi-Horizon Trajectory Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 mt-5">
        <div className="card-command p-3.5 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">CURRENT RISK</div>
          <div className="text-xl font-bold text-rose-400 font-mono-nums">
            {(riskData?.current_risk_score?.toFixed(1) || riskData?.risk_score?.toFixed(1) || '0.0')}
          </div>
          <div className="text-[10px] text-slate-500">Live Telemetry</div>
        </div>

        <div className="card-command p-3.5 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">FORECAST (+2 MIN)</div>
          <div className="text-xl font-bold text-amber-400 font-mono-nums">
            {(riskData?.predicted_risk_2min?.toFixed(1) || (riskData?.current_risk_score ? (riskData.current_risk_score + 1.5).toFixed(1) : '0.0'))}
          </div>
          <div className="text-[10px] text-amber-400/80 font-semibold">Immediate Window</div>
        </div>

        <div className="card-command p-3.5 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">FORECAST (+5 MIN)</div>
          <div className="text-xl font-bold text-rose-500 flex items-center gap-1 font-mono-nums">
            {(riskData?.predicted_risk_5min?.toFixed(1) || '0.0')}
            <TrendingUp className="w-4 h-4 text-rose-400 animate-pulse" />
          </div>
          <div className="text-[10px] text-rose-400 font-semibold">Tactical Horizon</div>
        </div>

        <div className="card-command p-3.5 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">FORECAST (+10 MIN)</div>
          <div className="text-xl font-bold text-purple-400 font-mono-nums">
            {(riskData?.predicted_risk_10min?.toFixed(1) || '0.0')}
          </div>
          <div className="text-[10px] text-purple-300 font-semibold">Strategic Horizon</div>
        </div>

        <div className="card-command p-3.5 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">INFLOW VS OUTFLOW</div>
          <div className="text-xl font-bold text-cyan-400 font-mono-nums">
            {riskData?.inflow ?? 0} vs {riskData?.outflow ?? 0}
          </div>
          <div className="text-[10px] text-slate-400">Pedestrians / min</div>
        </div>

        <div className="card-command p-3.5 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">TRAJECTORY TREND</div>
          <div className="text-xs font-black text-amber-300 uppercase tracking-tight truncate">
            {riskData?.trajectory_trend || 'STABLE'}
          </div>
          <div className="text-[10px] text-slate-400">Multi-Horizon Shape</div>
        </div>
      </div>

      {/* 2. XAI Explainability Text & Ranked Risk Factors */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-5">
        <div className="lg:col-span-7 card-command p-5 space-y-4">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            EXPLAINABLE AI (XAI) DIAGNOSTIC BREAKDOWN
          </h2>

          {/* Panic Propagation incoming risk explanation line */}
          {riskData?.propagation?.explanation_line && (
            <div className="p-3 rounded-xl bg-purple-950/70 border border-purple-500/50 text-xs font-bold text-purple-200 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-purple-400 animate-pulse flex-shrink-0" />
              <span>{riskData.propagation.explanation_line}</span>
            </div>
          )}

          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-sans">
            {riskData?.explanation ||
              riskData?.xai_summary ||
              'Baseline spatial telemetry active. No active crowd pressure escalation or directional bottleneck detected for this sector.'}
          </div>

          <div className="space-y-2">
            <div className="text-[11px] font-bold text-slate-400">RANKED PHYSICAL RISK CONTRIBUTORS:</div>
            <div className="space-y-2">
              {riskData?.ranked_risk_factors && riskData.ranked_risk_factors.length > 0 ? (
                riskData.ranked_risk_factors.map((f: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950/50 border border-slate-800 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center space-x-2">
                      <span className="w-5 h-5 rounded bg-slate-800 text-slate-300 font-bold flex items-center justify-center text-[10px] font-mono-nums">
                        #{idx + 1}
                      </span>
                      <span className="font-semibold text-slate-200">{f.factor}</span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-rose-400 font-bold font-mono-nums">{f.impact}</span>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        {f.severity}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/60 text-xs text-slate-400 text-center">
                  No elevated physical risk factors detected in current telemetry snapshot.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 3. Recommended Actions & AI Simulation Control (5 cols) */}
        <div className="lg:col-span-5 card-command p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <h2 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              AI RECOMMENDED INTERVENTIONS
            </h2>

            {/* Selectable Action List for Simulation */}
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-slate-400">SELECT INTERVENTION TO SIMULATE:</label>
              <div className="space-y-1.5">
                {selectableActions.map((act) => {
                  const isSelected = proposedAction.includes(act.action_type);
                  return (
                    <button
                      key={act.action_type}
                      type="button"
                      onClick={() => setProposedAction(act.description)}
                      className={`w-full text-left p-2.5 rounded-xl border transition flex items-center justify-between ${
                        isSelected
                          ? 'bg-cyan-950/60 border-cyan-500 text-cyan-200 shadow-md'
                          : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-cyan-400 animate-pulse' : 'bg-slate-700'}`} />
                        <span className="text-xs font-bold">{act.title}</span>
                      </div>
                      <span className="text-[10px] font-mono-nums px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                        {act.action_type}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Active Action Description Editor */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-400">PROPOSED INTERVENTION DIRECTIVE</label>
              <textarea
                value={proposedAction}
                onChange={(e) => setProposedAction(e.target.value)}
                className="w-full h-16 p-3 rounded-xl bg-slate-950 border border-slate-700/60 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono-nums"
              />
            </div>

            {/* SIMULATE Button */}
            <button
              onClick={handleSimulate}
              disabled={simulating}
              className="btn-primary w-full py-2.5 flex items-center justify-center gap-2 text-xs"
            >
              <Play className="w-4 h-4 fill-white" />
              {simulating ? 'RUNNING WHAT-IF PHYSICS SIMULATION...' : 'RUN WHAT-IF RISK SIMULATION'}
            </button>

            {/* Simulation Delta Result */}
            {simResult && (
              <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/40 space-y-3 animate-fadeIn">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-emerald-400">SIMULATION RESULT:</span>
                  <span className="text-[10px] text-emerald-300 font-bold font-mono-nums">
                    -{simResult.risk_reduction?.toFixed(1) || '38.0'} RISK DELTA
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-500/30">
                    <div className="text-[10px] text-slate-400 font-bold">CURRENT RISK</div>
                    <div className="text-xl font-bold text-rose-400 font-mono-nums">{simResult.current_risk}</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30">
                    <div className="text-[10px] text-slate-400 font-bold">PROJECTED AFTER</div>
                    <div className="text-xl font-bold text-emerald-400 font-mono-nums">{simResult.projected_risk}</div>
                  </div>
                </div>

                <p className="text-[11px] text-slate-300 italic">{simResult.explanation}</p>
              </div>
            )}

            {/* Drafted Public Announcement Editor with Language Tabs */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
                  PUBLIC ANNOUNCEMENT DRAFT
                </label>

                {/* Multi-Language Tabs */}
                <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
                  <button
                    type="button"
                    onClick={() => setSelectedLang('en')}
                    className={`px-2.5 py-0.5 text-[10px] font-bold rounded transition ${
                      selectedLang === 'en'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    EN (English)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedLang('hi')}
                    className={`px-2.5 py-0.5 text-[10px] font-bold rounded transition ${
                      selectedLang === 'hi'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    HI (हिंदी)
                  </button>
                </div>
              </div>

              <textarea
                value={draftedAnnouncement}
                onChange={(e) => setDraftedAnnouncement(e.target.value)}
                placeholder="Drafted PA announcement text..."
                className="w-full h-20 p-3 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans leading-relaxed"
              />

              <div className="flex justify-between items-center text-[10px] text-slate-500">
                <span>Language: {selectedLang.toUpperCase()} | Editable before broadcast dispatch</span>
                {draftedAnnouncement !== originalDraft && (
                  <span className="text-amber-400 font-bold">* Operator Modified</span>
                )}
              </div>
            </div>
          </div>

          {/* APPROVE / MODIFY / REJECT Action Controls */}
          <div className="pt-4 border-t border-slate-800 grid grid-cols-3 gap-2">
            <button
              onClick={() => {
                setPendingDecision('approved');
                setShowConfirmModal(true);
              }}
              className="py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition shadow-lg flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              APPROVE
            </button>
            <button
              onClick={() => {
                setPendingDecision('modified');
                setShowConfirmModal(true);
              }}
              className="py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-xl text-xs transition shadow-lg flex items-center justify-center gap-1.5"
            >
              <Edit3 className="w-4 h-4" />
              MODIFY
            </button>
            <button
              onClick={() => {
                setPendingDecision('rejected');
                setShowConfirmModal(true);
              }}
              className="btn-danger py-2.5 text-xs flex items-center justify-center gap-1.5"
            >
              <XCircle className="w-4 h-4" />
              REJECT
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Step Modal before Dispatch */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="card-command p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-amber-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="font-extrabold text-base text-white uppercase">
                CONFIRM OPERATOR DISPATCH DIRECTIVE
              </h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to mark this recommendation as{' '}
              <strong className="text-cyan-400 uppercase">{pendingDecision}</strong>? This action will immediately log operator audit entries, dispatch field officer squads, and broadcast the approved announcement.
            </p>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono-nums text-cyan-300">
              {proposedAction}
            </div>

            {draftedAnnouncement && (
              <div className="p-3 rounded-lg bg-slate-950 border border-cyan-500/30 text-xs text-slate-300">
                <div className="text-[10px] text-cyan-400 font-bold mb-1 uppercase">FINAL APPROVED ANNOUNCEMENT ({selectedLang.toUpperCase()}):</div>
                "{draftedAnnouncement}"
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="btn-secondary text-xs py-2 px-4"
              >
                CANCEL
              </button>
              <button
                onClick={handleConfirmDecision}
                className="btn-primary text-xs py-2 px-5"
              >
                CONFIRM & DISPATCH &rarr;
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
