'use client';

import React, { useState } from 'react';
import { CanonicalIncidentStatus } from '@/types/incident';
import { AlertTriangle, CheckCircle2, ShieldAlert, X, Loader2 } from 'lucide-react';

interface IncidentTransitionDialogProps {
  isOpen: boolean;
  incidentId: string;
  currentStatus: CanonicalIncidentStatus;
  targetStatus: CanonicalIncidentStatus;
  onClose: () => void;
  onConfirm: (targetStatus: CanonicalIncidentStatus, reason: string) => Promise<void>;
}

export function IncidentTransitionDialog({
  isOpen,
  incidentId,
  currentStatus,
  targetStatus,
  onClose,
  onConfirm,
}: IncidentTransitionDialogProps) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const isFalsePositive = targetStatus === 'FALSE_POSITIVE';
  const isResolved = targetStatus === 'RESOLVED';
  const isMitigating = targetStatus === 'MITIGATING';

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isFalsePositive && !reason.trim()) {
      setErrorMsg('A justification reason is required for marking an incident as False Positive.');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);
      await onConfirm(targetStatus, reason.trim());
      setReason('');
      onClose();
    } catch (err: any) {
      console.error('Transition dialog submission error:', err);
      setErrorMsg(err.message || 'Failed to complete incident status transition.');
    } finally {
      setSubmitting(false);
    }
  };

  const getDialogTitle = () => {
    switch (targetStatus) {
      case 'ACKNOWLEDGED':
        return 'ACKNOWLEDGE INCIDENT';
      case 'INVESTIGATING':
        return 'START INCIDENT INVESTIGATION';
      case 'MITIGATING':
        return 'MARK INCIDENT AS MITIGATING';
      case 'RESOLVED':
        return 'RESOLVE OPERATIONAL INCIDENT';
      case 'FALSE_POSITIVE':
        return 'MARK INCIDENT AS FALSE POSITIVE';
      default:
        return `TRANSITION TO ${targetStatus}`;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            {isFalsePositive ? (
              <AlertTriangle className="w-5 h-5 text-slate-400" />
            ) : isResolved ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-amber-400" />
            )}
            <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">
              {getDialogTitle()}
            </h3>
          </div>
          <button
            onClick={onClose}
            disabled={submitting}
            className="p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1 font-sans">
            <div className="flex justify-between text-slate-400">
              <span>Incident Reference:</span>
              <span className="font-bold text-white font-mono-nums">{incidentId}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Current Status:</span>
              <span className="font-bold text-amber-400">{currentStatus}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Target Lifecycle Status:</span>
              <span className="font-bold text-cyan-400">{targetStatus}</span>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/50 text-rose-300 text-xs font-sans">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleConfirm} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wide">
                {isFalsePositive
                  ? 'JUSTIFICATION REASON (REQUIRED):'
                  : isResolved
                  ? 'RESOLUTION OPERATIONAL NOTES (RECOMMENDED):'
                  : 'OPERATOR TRANSITION NOTES (OPTIONAL):'}
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={
                  isFalsePositive
                    ? 'State why this warning was classified as a false alarm...'
                    : isResolved
                    ? 'Detail ground conditions or mitigation action that resolved the incident...'
                    : 'Add notes for the audit log...'
                }
                rows={3}
                disabled={submitting}
                className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 text-xs font-sans"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="btn-secondary py-2 px-4 text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className={`py-2 px-4 rounded-xl font-bold text-xs text-white transition flex items-center gap-2 ${
                  isFalsePositive
                    ? 'bg-slate-700 hover:bg-slate-600'
                    : isResolved
                    ? 'bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-950/50'
                    : 'bg-cyan-600 hover:bg-cyan-500 shadow-lg shadow-cyan-950/50'
                } disabled:opacity-50`}
              >
                {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{submitting ? 'Updating...' : 'Confirm Action'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
