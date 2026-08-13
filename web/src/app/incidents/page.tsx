'use client';

import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Skeleton } from '@/components/ui/Skeleton';
import { api, IncidentData } from '@/lib/api';
import {
  AlertTriangle,
  Filter,
  Eye,
  MapPin,
  ChevronRight,
  X,
} from 'lucide-react';

export default function IncidentsPage() {
  const [loading, setLoading] = useState(true);
  const [incidents, setIncidents] = useState<IncidentData[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedIncident, setSelectedIncident] = useState<IncidentData | null>(null);

  useEffect(() => {
    async function loadIncidents() {
      const data = await api.fetchIncidents();
      setIncidents(data);
      setLoading(false);
    }
    loadIncidents();
  }, []);

  const handleUpdateStatus = async (id: string, newStatus: IncidentData['status']) => {
    await api.updateIncidentStatus(id, newStatus);
    setIncidents((prev) =>
      prev.map((inc) => (inc.id === id ? { ...inc, status: newStatus } : inc))
    );
    if (selectedIncident?.id === id) {
      setSelectedIncident((prev) => (prev ? { ...prev, status: newStatus } : null));
    }
  };

  const filteredIncidents = incidents.filter(
    (inc) => statusFilter === 'all' || inc.status === statusFilter
  );

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-rose-400" />
            INCIDENT REPORT STREAM
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time citizen crowd reports & verified field officer observations.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center space-x-2 bg-slate-900 p-1.5 rounded-xl border border-slate-800 text-xs">
          <Filter className="w-4 h-4 text-slate-400 ml-2" />
          {['all', 'pending', 'verified', 'resolving', 'resolved', 'false_alarm'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg font-semibold capitalize transition ${
                statusFilter === st
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Incidents Table & Detail Drawer Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-5">
        {/* Main Incident Table (8 cols or 12 cols if drawer closed) */}
        <div className={selectedIncident ? 'lg:col-span-7' : 'lg:col-span-12'}>
          <div className="card-command overflow-hidden shadow-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">INCIDENT TYPE</th>
                  <th className="py-3.5 px-4">LOCATION / ZONE</th>
                  <th className="py-3.5 px-4">REPORTER</th>
                  <th className="py-3.5 px-4">STATUS</th>
                  <th className="py-3.5 px-4 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {loading ? (
                  Array(4)
                    .fill(0)
                    .map((_, i) => (
                      <tr key={i}>
                        <td colSpan={5} className="py-4 px-4">
                          <Skeleton className="h-8 w-full" />
                        </td>
                      </tr>
                    ))
                ) : filteredIncidents.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No incident reports matching status &ldquo;{statusFilter}&rdquo;.
                    </td>
                  </tr>
                ) : (
                  filteredIncidents.map((inc) => (
                    <tr
                      key={inc.id}
                      onClick={() => setSelectedIncident(inc)}
                      className={`hover:bg-slate-800/40 transition cursor-pointer ${
                        selectedIncident?.id === inc.id ? 'bg-cyan-950/30' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-bold text-white flex items-center gap-2">
                        <span>{inc.type}</span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        <div className="font-semibold">{inc.location_name}</div>
                        <div className="text-[10px] text-slate-500 font-mono-nums">Zone ID: {inc.zone_id}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                            inc.user_role === 'field_officer'
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                              : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                          }`}
                        >
                          {inc.reported_by}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2.5 py-1 text-[10px] font-black rounded-full uppercase border ${
                            inc.status === 'pending'
                              ? 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse'
                              : inc.status === 'verified'
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                              : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          }`}
                        >
                          {inc.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedIncident(inc);
                          }}
                          className="btn-secondary text-[11px] py-1 px-2.5 inline-flex items-center gap-1"
                        >
                          Inspect <ChevronRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detail Drawer (5 cols) */}
        {selectedIncident && (
          <div className="lg:col-span-5 card-command p-5 space-y-4 animate-fadeIn shadow-2xl flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-rose-400" />
                  <h3 className="font-extrabold text-sm text-white">INCIDENT DETAILS</h3>
                </div>
                <button
                  onClick={() => setSelectedIncident(null)}
                  className="p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <h4 className="text-base font-black text-white">{selectedIncident.type}</h4>
                  <div className="text-xs text-slate-400 flex items-center gap-1 mt-1 font-mono-nums">
                    <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                    {selectedIncident.location_name} ({selectedIncident.lat}, {selectedIncident.lng})
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans">
                  {selectedIncident.description}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-500 font-bold">REPORTER</div>
                    <div className="font-semibold text-slate-200">{selectedIncident.reported_by}</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-500 font-bold">REPORTED TIME</div>
                    <div className="font-semibold text-slate-200 font-mono-nums">3 minutes ago</div>
                  </div>
                </div>

                {/* Evidence Photo Preview */}
                <div className="space-y-1">
                  <div className="text-[10px] font-bold text-slate-400">CAMERA EVIDENCE ATTACHMENT</div>
                  <div className="h-36 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-500 text-xs overflow-hidden">
                    <div className="text-center p-4">
                      <Eye className="w-6 h-6 mx-auto mb-1 text-slate-600" />
                      <span>GPS Tagged Photo Captured via Field App</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Status Override Controls */}
            <div className="pt-4 border-t border-slate-800 space-y-2">
              <div className="text-[11px] font-bold text-slate-400">UPDATE INCIDENT TRIAGE STATUS:</div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => handleUpdateStatus(selectedIncident.id, 'verified')}
                  className="py-2 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-lg text-xs transition"
                >
                  VERIFY
                </button>
                <button
                  onClick={() => handleUpdateStatus(selectedIncident.id, 'resolved')}
                  className="py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs transition"
                >
                  RESOLVED
                </button>
                <button
                  onClick={() => handleUpdateStatus(selectedIncident.id, 'false_alarm')}
                  className="btn-secondary py-2 text-xs text-center justify-center"
                >
                  FALSE ALARM
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
