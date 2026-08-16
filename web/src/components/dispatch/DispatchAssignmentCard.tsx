'use client';

import React, { useState } from 'react';
import { User, Clock, Shield, CheckCircle, Navigation, Radio, MapPin, AlertCircle } from 'lucide-react';
import { DispatchAssignment, DispatchStatus, VALID_DISPATCH_TRANSITIONS } from '@/types/dispatch';

interface DispatchAssignmentCardProps {
  dispatch: DispatchAssignment;
  onTransition?: (dispatchId: string, newStatus: DispatchStatus, reason?: string) => Promise<void>;
  isOperatorView?: boolean;
}

export const DispatchAssignmentCard: React.FC<DispatchAssignmentCardProps> = ({
  dispatch,
  onTransition,
  isOperatorView = true,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionReason, setActionReason] = useState('');
  const [activeActionModal, setActiveActionModal] = useState<DispatchStatus | null>(null);

  const allowedTransitions = VALID_DISPATCH_TRANSITIONS[dispatch.status] || [];

  const getStatusBadge = (status: DispatchStatus) => {
    switch (status) {
      case 'ASSIGNED':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/40';
      case 'ACKNOWLEDGED':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/40';
      case 'EN_ROUTE':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'ON_SCENE':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/40';
      case 'RESPONDING':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
      case 'COMPLETED':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'CANCELLED':
        return 'bg-slate-700/50 text-slate-400 border-slate-600';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const handleExecuteTransition = async (targetStatus: DispatchStatus) => {
    if (!onTransition) return;
    setIsSubmitting(true);
    try {
      await onTransition(dispatch.dispatch_id, targetStatus, actionReason || undefined);
      setActionReason('');
      setActiveActionModal(null);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg">
      <div className="flex items-start justify-between border-b border-slate-800/80 pb-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-cyan-400">{dispatch.dispatch_id}</span>
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider ${getStatusBadge(dispatch.status)}`}>
              {dispatch.status}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400 flex items-center gap-1.5">
            <User className="h-3.5 w-3.5 text-slate-500" />
            <span className="font-semibold text-slate-200">{dispatch.officer?.name || dispatch.officer_id}</span>
          </p>
        </div>

        {dispatch.eta_minutes && (
          <div className="flex items-center gap-1 rounded-md bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-400 border border-blue-500/20">
            <Clock className="h-3.5 w-3.5" />
            <span>ETA: {dispatch.eta_minutes}m</span>
          </div>
        )}
      </div>

      {dispatch.dispatch_reason && (
        <div className="mb-3 rounded-lg bg-slate-950/60 p-2.5 text-xs text-slate-300 border border-slate-800">
          <span className="font-semibold text-slate-400 block mb-0.5">Dispatch Reason:</span>
          {dispatch.dispatch_reason}
        </div>
      )}

      {/* Timestamp Progression */}
      <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 mb-3 bg-slate-950/30 p-2 rounded-md">
        <div>Assigned: <span className="text-slate-200">{new Date(dispatch.assigned_at).toLocaleTimeString()}</span></div>
        {dispatch.acknowledged_at && <div>Ack: <span className="text-purple-300">{new Date(dispatch.acknowledged_at).toLocaleTimeString()}</span></div>}
        {dispatch.en_route_at && <div>En Route: <span className="text-amber-300">{new Date(dispatch.en_route_at).toLocaleTimeString()}</span></div>}
        {dispatch.on_scene_at && <div>On Scene: <span className="text-orange-300">{new Date(dispatch.on_scene_at).toLocaleTimeString()}</span></div>}
        {dispatch.completed_at && <div>Completed: <span className="text-emerald-300">{new Date(dispatch.completed_at).toLocaleTimeString()}</span></div>}
      </div>

      {/* Allowed Action Buttons */}
      {allowedTransitions.length > 0 && onTransition && (
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
          {allowedTransitions.map((target) => (
            <button
              key={target}
              onClick={() => setActiveActionModal(target)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all shadow-sm ${
                target === 'CANCELLED'
                  ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30'
                  : target === 'COMPLETED'
                  ? 'bg-emerald-600 text-white hover:bg-emerald-500 shadow-emerald-600/20'
                  : 'bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700'
              }`}
            >
              {target === 'ACKNOWLEDGED' && <CheckCircle className="h-3.5 w-3.5 text-purple-400" />}
              {target === 'EN_ROUTE' && <Navigation className="h-3.5 w-3.5 text-amber-400" />}
              {target === 'ON_SCENE' && <MapPin className="h-3.5 w-3.5 text-orange-400" />}
              {target === 'RESPONDING' && <Radio className="h-3.5 w-3.5 text-cyan-400" />}
              {target === 'COMPLETED' && <CheckCircle className="h-3.5 w-3.5 text-white" />}
              <span>{target.replace('_', ' ')}</span>
            </button>
          ))}
        </div>
      )}

      {/* Quick Action Modal */}
      {activeActionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-xl">
            <h4 className="text-sm font-bold text-white mb-2">
              Transition to <span className="text-cyan-400">{activeActionModal}</span>
            </h4>
            <p className="text-xs text-slate-400 mb-3">
              Add optional operational notes for this state transition:
            </p>
            <textarea
              rows={2}
              value={actionReason}
              onChange={(e) => setActionReason(e.target.value)}
              placeholder="Operational notes..."
              className="w-full rounded-lg border border-slate-700 bg-slate-800 p-2 text-xs text-white placeholder-slate-500 focus:outline-none"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setActiveActionModal(null)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => handleExecuteTransition(activeActionModal)}
                disabled={isSubmitting}
                className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {isSubmitting ? 'Updating...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
