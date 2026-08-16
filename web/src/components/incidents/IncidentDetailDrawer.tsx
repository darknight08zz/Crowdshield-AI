'use client';

import React, { useState, useEffect } from 'react';
import { IncidentCanonicalData, CanonicalIncidentStatus } from '@/types/incident';
import { DispatchAssignment, DispatchStatus } from '@/types/dispatch';
import { api } from '@/lib/api';
import { IncidentStatusBadge } from './IncidentStatusBadge';
import { IncidentSeverityBadge } from './IncidentSeverityBadge';
import { IncidentSnapshotPanel } from './IncidentSnapshotPanel';
import { IncidentTimeline } from './IncidentTimeline';
import { IncidentProvenancePanel } from './IncidentProvenancePanel';
import { IncidentActionPanel } from './IncidentActionPanel';
import { IncidentTransitionDialog } from './IncidentTransitionDialog';
import { DispatchAssignmentDialog } from '../dispatch/DispatchAssignmentDialog';
import { DispatchAssignmentCard } from '../dispatch/DispatchAssignmentCard';
import { DispatchTimeline } from '../dispatch/DispatchTimeline';
import { AlertTriangle, MapPin, X, Map, Target, UserCheck, Plus, Shield } from 'lucide-react';
import Link from 'next/link';

interface IncidentDetailDrawerProps {
  incident: IncidentCanonicalData | null;
  onClose: () => void;
  onTransitionSuccess: (updatedIncident: IncidentCanonicalData) => void;
  onTransitionExecute: (targetStatus: CanonicalIncidentStatus, reason: string) => Promise<void>;
}

export function IncidentDetailDrawer({
  incident,
  onClose,
  onTransitionSuccess,
  onTransitionExecute,
}: IncidentDetailDrawerProps) {
  const [dialogTarget, setDialogTarget] = useState<CanonicalIncidentStatus | null>(null);
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState<boolean>(false);
  const [dispatches, setDispatches] = useState<DispatchAssignment[]>([]);

  useEffect(() => {
    if (incident) {
      loadDispatches();
    }
  }, [incident?.incident_id]);

  const loadDispatches = async () => {
    if (!incident) return;
    try {
      const list = await api.fetchIncidentDispatches(incident.incident_id);
      setDispatches(list);
    } catch (e) {
      console.error('Failed to load incident dispatches', e);
    }
  };

  const handleDispatchTransition = async (dispatchId: string, newStatus: DispatchStatus, reason?: string) => {
    try {
      await api.transitionDispatchStatus(dispatchId, { new_status: newStatus, reason });
      await loadDispatches();
    } catch (e) {
      console.error(e);
    }
  };

  if (!incident) return null;

  const isTerminal = incident.status === 'RESOLVED' || incident.status === 'FALSE_POSITIVE';

  return (
    <div className="card-command p-5 space-y-5 animate-fadeIn shadow-2xl flex flex-col justify-between overflow-y-auto max-h-[85vh]">
      <div className="space-y-5">
        {/* Header / Identity */}
        <div className="flex justify-between items-start pb-3 border-b border-slate-800">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
              <h3 className="font-black text-base text-white font-mono-nums">
                {incident.incident_id}
              </h3>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-2">
              <span className="font-semibold text-slate-300">Event: {incident.event_id}</span>
              <span>·</span>
              <span className="font-semibold text-cyan-400">Zone: {incident.zone_id}</span>
              {incident.camera_id && (
                <>
                  <span>·</span>
                  <span className="font-mono-nums text-slate-400">Cam: {incident.camera_id}</span>
                </>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current Lifecycle Status & Warning Header */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <div className="text-[10px] font-bold text-slate-500 uppercase">LIFECYCLE STATUS</div>
            <div>
              <IncidentStatusBadge status={incident.status} />
            </div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <div className="text-[10px] font-bold text-slate-500 uppercase">CURRENT WARNING STATE</div>
            <div>
              <IncidentSeverityBadge
                warningState={incident.latest_snapshot?.latest_warning_state || incident.creation_snapshot?.warning_state_at_creation}
              />
            </div>
          </div>
        </div>

        {/* Map & Zone Navigation Shortcuts */}
        <div className="flex items-center gap-2">
          <Link
            href={`/zones/${incident.zone_id}`}
            className="flex-1 py-2 px-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-cyan-500/40 text-xs font-bold text-cyan-400 flex items-center justify-center gap-2 transition"
          >
            <Target className="w-4 h-4" />
            <span>VIEW ZONE DETAIL</span>
          </Link>
          <Link
            href={`/overview?zone=${incident.zone_id}`}
            className="flex-1 py-2 px-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-cyan-500/40 text-xs font-bold text-cyan-400 flex items-center justify-center gap-2 transition"
          >
            <Map className="w-4 h-4" />
            <span>VIEW ON GEOSPATIAL MAP</span>
          </Link>
        </div>

        {/* FIELD DISPATCH CONTROL SECTION */}
        <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-blue-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-300">
                Field Officer Dispatch
              </h4>
            </div>
            {!isTerminal && (
              <button
                onClick={() => setIsDispatchModalOpen(true)}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white shadow-md hover:bg-blue-500 transition"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>DISPATCH OFFICER</span>
              </button>
            )}
          </div>

          {dispatches.length === 0 ? (
            <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-3 text-center text-xs text-slate-400">
              No field response officer currently dispatched for this incident.
            </div>
          ) : (
            <div className="space-y-3">
              {dispatches.map((dsp) => (
                <DispatchAssignmentCard
                  key={dsp.dispatch_id}
                  dispatch={dsp}
                  onTransition={handleDispatchTransition}
                  isOperatorView={true}
                />
              ))}
            </div>
          )}
        </div>

        {/* Operational Action Panel */}
        <IncidentActionPanel
          currentStatus={incident.status}
          onSelectAction={(target) => setDialogTarget(target)}
        />

        {/* Snapshot Panel */}
        <IncidentSnapshotPanel
          creationSnapshot={incident.creation_snapshot}
          latestSnapshot={incident.latest_snapshot}
          cameraHealthStatus={incident.camera_health_status}
          isStale={incident.is_stale}
          isDegraded={incident.is_degraded}
        />

        {/* Incident Audit Timeline */}
        <IncidentTimeline transitions={incident.transitions || []} />

        {/* Dispatch Audit Trail Timeline (if active dispatches) */}
        {dispatches.length > 0 && dispatches[0].transitions && (
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-slate-500 uppercase">Dispatch Audit Trail</h4>
            <DispatchTimeline transitions={dispatches[0].transitions} />
          </div>
        )}

        {/* AI Provenance Panel */}
        <IncidentProvenancePanel provenance={incident.provenance} />
      </div>

      {/* Confirmation Dialog Modal */}
      {dialogTarget && (
        <IncidentTransitionDialog
          isOpen={Boolean(dialogTarget)}
          incidentId={incident.incident_id}
          currentStatus={incident.status}
          targetStatus={dialogTarget}
          onClose={() => setDialogTarget(null)}
          onConfirm={async (targetStatus, reason) => {
            await onTransitionExecute(targetStatus, reason);
            setDialogTarget(null);
          }}
        />
      )}

      {/* Dispatch Assignment Modal */}
      <DispatchAssignmentDialog
        isOpen={isDispatchModalOpen}
        onClose={() => setIsDispatchModalOpen(false)}
        incidentId={incident.incident_id}
        incidentStatus={incident.status}
        zoneId={incident.zone_id}
        onSuccess={loadDispatches}
      />
    </div>
  );
}
