'use client';

import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Skeleton } from '@/components/ui/Skeleton';
import { api } from '@/lib/api';
import { CheckCircle2, TrendingDown, ShieldCheck, ArrowRight, RefreshCw, AlertCircle } from 'lucide-react';
import Link from 'next/link';

interface InterventionData {
  recommendation_id: string;
  action_title: string;
  approved_at: string;
  before_risk_score: number;
  after_risk_score: number;
  risk_reduction_points: number;
  risk_reduction_pct: number;
  outcome_verdict: string;
}

export default function VerifyResultPage() {
  const [loading, setLoading] = useState(true);
  const [latestIntervention, setLatestIntervention] = useState<InterventionData | null>(null);

  useEffect(() => {
    async function loadInterventionResult() {
      try {
        const events = await api.fetchEvents();
        if (events && events.length > 0) {
          const summary = await api.fetchEventAnalyticsSummary(events[0].id);
          if (summary && summary.intervention_effectiveness && summary.intervention_effectiveness.length > 0) {
            setLatestIntervention(summary.intervention_effectiveness[0]);
          }
        }
      } catch (err) {
        console.error('Error fetching verification data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadInterventionResult();
  }, []);

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            INTERVENTION RESULT & CLOSED-LOOP VERIFICATION
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Post-dispatch mitigation auditing confirming intervention effectiveness and crowd pressure relief.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-emerald-950/40 border border-emerald-500/30 px-3 py-1.5 rounded-xl text-xs text-emerald-300 font-semibold">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
          <span>REALTIME TRACKING: <strong className="text-white">ACTIVE</strong></span>
        </div>
      </div>

      {loading ? (
        <Skeleton className="h-64 w-full rounded-2xl" />
      ) : latestIntervention ? (
        <div className="space-y-6">
          {/* Main Success Verification Banner */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/80 via-slate-900 to-slate-950 border border-emerald-500/40 shadow-2xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <span className="px-3 py-1 text-[10px] font-black rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
                  VERIFIED SUCCESSFUL INTERVENTION
                </span>
                <h2 className="text-lg font-black text-white pt-1">
                  Risk Reduced by <span className="text-emerald-400">-{latestIntervention.risk_reduction_points.toFixed(1)} Points</span>
                </h2>
                <p className="text-xs text-slate-300">
                  Action Executed: <strong>{latestIntervention.action_title}</strong>
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/90 border border-emerald-500/30 text-center">
                <div className="text-[10px] font-bold text-slate-400">TOTAL RISK REDUCTION</div>
                <div className="text-3xl font-black text-emerald-400 flex items-center justify-center gap-1">
                  <TrendingDown className="w-6 h-6 text-emerald-400" />
                  -{latestIntervention.risk_reduction_pct.toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Before vs After Numbers */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-center space-y-1">
                <div className="text-[10px] font-bold text-slate-400">PRE-INTERVENTION RISK</div>
                <div className="text-2xl font-black text-rose-400">{latestIntervention.before_risk_score.toFixed(1)} / 100</div>
                <div className="text-[10px] text-rose-400 font-semibold">PRECURSOR SURGE ALARM</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-center">
                <ArrowRight className="w-8 h-8 text-cyan-400 animate-pulse" />
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/40 text-center space-y-1">
                <div className="text-[10px] font-bold text-slate-400">CURRENT (POST-DISPATCH) RISK</div>
                <div className="text-2xl font-black text-emerald-400">{latestIntervention.after_risk_score.toFixed(1)} / 100</div>
                <div className="text-[10px] text-emerald-400 font-semibold">{latestIntervention.outcome_verdict.replace('_', ' ')}</div>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Link
              href="/overview"
              className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-xs transition shadow-lg flex items-center gap-2"
            >
              Return to Command Overview &rarr;
            </Link>
          </div>
        </div>
      ) : (
        /* Empty State when no interventions exist */
        <div className="p-10 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4 shadow-xl">
          <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto" />
          <h2 className="text-lg font-bold text-white tracking-tight">SYSTEM STATUS NORMAL</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            No active or recent intervention dispatches recorded in the database. All venue sectors are operating under baseline risk control parameters.
          </p>
          <div className="pt-4 flex justify-center">
            <Link
              href="/overview"
              className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-500/30 font-bold rounded-xl text-xs transition shadow-md flex items-center gap-2"
            >
              Return to Command Overview &rarr;
            </Link>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
