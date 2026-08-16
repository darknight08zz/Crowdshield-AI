'use client';

import React, { useState, useEffect } from 'react';
import { UserCheck, ShieldAlert, Clock, AlertTriangle, X, Check } from 'lucide-react';
import { ResponseOfficer } from '@/types/dispatch';
import { api } from '@/lib/api';

interface DispatchAssignmentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  incidentId: string;
  incidentStatus: string;
  zoneId: string;
  onSuccess: () => void;
}

export const DispatchAssignmentDialog: React.FC<DispatchAssignmentDialogProps> = ({
  isOpen,
  onClose,
  incidentId,
  incidentStatus,
  zoneId,
  onSuccess,
}) => {
  const [officers, setOfficers] = useState<ResponseOfficer[]>([]);
  const [selectedOfficerId, setSelectedOfficerId] = useState<string>('');
  const [etaMinutes, setEtaMinutes] = useState<number>(5);
  const [reason, setReason] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setErrorMsg(null);
      setReason('');
      fetchOfficers();
    }
  }, [isOpen]);

  const fetchOfficers = async () => {
    try {
      const list = await api.fetchResponseOfficers();
      setOfficers(list);
      if (list.length > 0) {
        // Default to first available officer
        const available = list.find((o) => o.status === 'AVAILABLE');
        setSelectedOfficerId(available ? available.officer_id : list[0].officer_id);
      }
    } catch (e) {
      console.error('Failed to load officers', e);
    }
  };

  if (!isOpen) return null;

  const isTerminal = incidentStatus === 'RESOLVED' || incidentStatus === 'FALSE_POSITIVE';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOfficerId) {
      setErrorMsg('Please select a response officer or team.');
      return;
    }
    if (!reason.trim()) {
      setErrorMsg('Mandatory dispatch reason is required.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      await api.createDispatchAssignment(incidentId, {
        officer_id: selectedOfficerId,
        eta_minutes: etaMinutes,
        reason: reason.trim(),
      });
      setIsLoading(false);
      onSuccess();
      onClose();
    } catch (err: any) {
      setIsLoading(false);
      setErrorMsg(err.message || 'Failed to dispatch officer.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-5 border-b border-slate-800 pb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/20 text-blue-400">
            <UserCheck className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Create Field Dispatch Assignment</h3>
            <p className="text-xs text-slate-400">
              Incident: <span className="font-mono text-cyan-400">{incidentId}</span> ({zoneId})
            </p>
          </div>
        </div>

        {isTerminal ? (
          <div className="my-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-red-400" />
            <div>
              <p className="font-semibold">Terminal Incident State</p>
              <p className="text-xs text-red-400/80">
                Cannot create new dispatch assignments for resolved or false positive incidents.
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {errorMsg && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Assign Field Officer / Rapid Response Team
              </label>
              <select
                value={selectedOfficerId}
                onChange={(e) => setSelectedOfficerId(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              >
                {officers.map((off) => (
                  <option key={off.officer_id} value={off.officer_id}>
                    {off.name} ({off.officer_id}) — [{off.status}]
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Estimated Time of Arrival (ETA)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={etaMinutes}
                  onChange={(e) => setEtaMinutes(parseInt(e.target.value))}
                  className="w-full accent-blue-500"
                />
                <span className="flex items-center gap-1 min-w-[70px] rounded-md bg-slate-800 px-2 py-1 text-xs font-bold text-blue-400 border border-slate-700">
                  <Clock className="h-3.5 w-3.5" />
                  {etaMinutes} min
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Mandatory Operational Dispatch Reason
              </label>
              <textarea
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Specify tactical instructions or reason for field team deployment..."
                className="w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-xs font-bold text-white shadow-lg shadow-blue-600/30 hover:bg-blue-500 disabled:opacity-50"
              >
                {isLoading ? (
                  <span>Dispatching...</span>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    <span>Dispatch Officer</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
