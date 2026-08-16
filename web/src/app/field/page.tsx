'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  UserCheck,
  Clock,
  MapPin,
  CheckCircle,
  Navigation,
  Radio,
  AlertTriangle,
  Info,
  RefreshCw,
  Zap,
} from 'lucide-react';
import {
  DispatchAssignment,
  FieldOfficerAssignmentContext,
  DispatchStatus,
  VALID_DISPATCH_TRANSITIONS,
} from '@/types/dispatch';
import { api } from '@/lib/api';
import { DispatchAssignmentCard } from '@/components/dispatch/DispatchAssignmentCard';
import { DispatchTimeline } from '@/components/dispatch/DispatchTimeline';

export default function FieldOfficerActionCenterPage() {
  const [dispatches, setDispatches] = useState<DispatchAssignment[]>([]);
  const [selectedDispatchId, setSelectedDispatchId] = useState<string | null>(null);
  const [context, setContext] = useState<FieldOfficerAssignmentContext | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionReason, setActionReason] = useState<string>('');
  const [transitioningTarget, setTransitioningTarget] = useState<DispatchStatus | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadMyDispatches();
  }, []);

  useEffect(() => {
    if (selectedDispatchId) {
      loadContext(selectedDispatchId);
    } else {
      setContext(null);
    }
  }, [selectedDispatchId]);

  const loadMyDispatches = async () => {
    setIsLoading(true);
    try {
      const list = await api.fetchMyFieldDispatches();
      setDispatches(list);
      if (list.length > 0 && !selectedDispatchId) {
        setSelectedDispatchId(list[0].dispatch_id);
      }
    } catch (e) {
      console.error('Failed to load field dispatches', e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadContext = async (dispatchId: string) => {
    try {
      const ctx = await api.fetchFieldDispatchContext(dispatchId);
      setContext(ctx);
    } catch (e) {
      console.error('Failed to load dispatch context', e);
    }
  };

  const handleTransition = async (targetStatus: DispatchStatus) => {
    if (!selectedDispatchId) return;
    try {
      setErrorMsg(null);
      await api.transitionFieldDispatchStatus(selectedDispatchId, {
        new_status: targetStatus,
        reason: actionReason.trim() || undefined,
      });
      setActionReason('');
      setTransitioningTarget(null);
      await loadMyDispatches();
      if (selectedDispatchId) {
        await loadContext(selectedDispatchId);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update status.');
    }
  };

  const selectedDispatch = dispatches.find((d) => d.dispatch_id === selectedDispatchId);
  const allowedTransitions = selectedDispatch
    ? VALID_DISPATCH_TRANSITIONS[selectedDispatch.status] || []
    : [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      {/* Top Header */}
      <header className="mb-6 flex flex-col gap-4 border-b border-slate-800 pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <UserCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-white md:text-2xl">
                Field Officer Response Center
              </h1>
              <p className="text-xs text-slate-400">
                Tactical Field Dispatch Execution & Realtime Incident Intelligence
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            FIELD_OFFICER ROLE
          </span>
          <button
            onClick={loadMyDispatches}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Assigned Dispatches List */}
        <div className="space-y-4 lg:col-span-1">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Assigned Field Dispatches ({dispatches.length})
          </h2>

          {isLoading ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center text-xs text-slate-400">
              Loading active field assignments...
            </div>
          ) : dispatches.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center text-xs text-slate-500">
              No active dispatches currently assigned to you.
            </div>
          ) : (
            <div className="space-y-3">
              {dispatches.map((dsp) => {
                const isSelected = dsp.dispatch_id === selectedDispatchId;
                return (
                  <div
                    key={dsp.dispatch_id}
                    onClick={() => setSelectedDispatchId(dsp.dispatch_id)}
                    className={`cursor-pointer transition-all ${
                      isSelected ? 'ring-2 ring-blue-500 rounded-xl' : ''
                    }`}
                  >
                    <DispatchAssignmentCard
                      dispatch={dsp}
                      isOperatorView={false}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Dispatch Context & Action Panel */}
        <div className="lg:col-span-2 space-y-6">
          {context && selectedDispatch ? (
            <>
              {/* Field Officer Context Box */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl space-y-5">
                <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-4 gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-cyan-400">
                        {context.dispatch.dispatch_id}
                      </span>
                      <span className="inline-flex items-center rounded-full bg-blue-500/20 px-2.5 py-0.5 text-xs font-extrabold text-blue-400 border border-blue-500/30">
                        {context.dispatch.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      Incident: <span className="font-mono text-slate-200">{context.incident_id}</span> | Zone:{' '}
                      <span className="font-bold text-cyan-400">{context.zone_id}</span> | Event:{' '}
                      <span className="text-slate-300">{context.event_id}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-400">WARNING:</span>
                    <span className="rounded-md bg-rose-500/20 px-3 py-1 text-xs font-black text-rose-400 border border-rose-500/30">
                      {context.warning_state}
                    </span>
                  </div>
                </div>

                {/* Risk Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Physics Risk */}
                  <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold text-slate-400">PHYSICS RISK SCORE</span>
                      <span className="font-mono font-bold text-amber-400">
                        {((context.physics_risk || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-amber-500 to-rose-500 transition-all duration-300"
                        style={{ width: `${Math.min(100, (context.physics_risk || 0) * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* AI Probability */}
                  <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold text-slate-400">AI ESCALATION PROBABILITY</span>
                      <span className="font-mono font-bold text-cyan-400">
                        {context.ai_probability !== undefined && context.ai_probability !== null
                          ? `${(context.ai_probability * 100).toFixed(1)}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                        style={{
                          width: `${Math.min(100, (context.ai_probability || 0) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* MANDATORY AI PROTOTYPE DISCLAIMER BOX */}
                <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-xs text-amber-200 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-extrabold uppercase tracking-wide text-amber-300">
                      OPERATIONAL DISCLAIMER & PROTOTYPE ADVISORY
                    </p>
                    <p className="text-amber-200/90 leading-relaxed">
                      {context.disclaimer}
                    </p>
                    <div className="pt-1 text-[11px] text-amber-400/80 font-mono">
                      Model Version: {context.model_version} | Status: {context.model_status} | Label:{' '}
                      {context.label_type}
                    </div>
                  </div>
                </div>

                {/* Field Officer Transition Action Control */}
                {allowedTransitions.length > 0 && (
                  <div className="space-y-3 pt-3 border-t border-slate-800">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Update Dispatch Status
                    </h3>

                    {errorMsg && (
                      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
                        {errorMsg}
                      </div>
                    )}

                    <div className="flex flex-wrap items-center gap-3">
                      {allowedTransitions.map((targetStatus) => (
                        <button
                          key={targetStatus}
                          onClick={() => setTransitioningTarget(targetStatus)}
                          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-black tracking-wide shadow-md transition-all ${
                            targetStatus === 'ACKNOWLEDGED'
                              ? 'bg-purple-600 hover:bg-purple-500 text-white'
                              : targetStatus === 'EN_ROUTE'
                              ? 'bg-amber-600 hover:bg-amber-500 text-white'
                              : targetStatus === 'ON_SCENE'
                              ? 'bg-orange-600 hover:bg-orange-500 text-white'
                              : targetStatus === 'RESPONDING'
                              ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                              : targetStatus === 'COMPLETED'
                              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30'
                              : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                          }`}
                        >
                          {targetStatus === 'ACKNOWLEDGED' && <CheckCircle className="h-4 w-4" />}
                          {targetStatus === 'EN_ROUTE' && <Navigation className="h-4 w-4" />}
                          {targetStatus === 'ON_SCENE' && <MapPin className="h-4 w-4" />}
                          {targetStatus === 'RESPONDING' && <Radio className="h-4 w-4" />}
                          {targetStatus === 'COMPLETED' && <Zap className="h-4 w-4" />}
                          <span>MARK AS {targetStatus.replace('_', ' ')}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Audit Timeline */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Dispatch Lifecycle Audit Trail
                </h3>
                <DispatchTimeline transitions={selectedDispatch.transitions || []} />
              </div>
            </>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-12 text-center text-sm text-slate-500">
              Select a dispatch assignment from the left list to view field intelligence context.
            </div>
          )}
        </div>
      </div>

      {/* Transition Reason Modal */}
      {transitioningTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">
              Confirm Transition to <span className="text-cyan-400">{transitioningTarget}</span>
            </h3>
            <p className="text-xs text-slate-400">
              Add optional tactical status notes (e.g. initial on-scene observations, crowd control tactics active):
            </p>
            <textarea
              rows={3}
              value={actionReason}
              onChange={(e) => setActionReason(e.target.value)}
              placeholder="Status update notes..."
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-xs text-white placeholder-slate-500 focus:outline-none"
            />
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setTransitioningTarget(null)}
                className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => handleTransition(transitioningTarget)}
                className="rounded-lg bg-blue-600 px-5 py-2 text-xs font-bold text-white shadow-lg hover:bg-blue-500"
              >
                Confirm Update
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
