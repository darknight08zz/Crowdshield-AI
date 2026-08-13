'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Sliders,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Trash2,
  Save,
  Users,
  Bell,
  Layers,
  DoorClosed,
  ArrowLeft,
} from 'lucide-react';
import { api, EventData, ZoneData, GateData, NotificationPolicyRule } from '@/lib/api';

export default function EventAdminPage() {
  const [activeTab, setActiveTab] = useState<'settings' | 'venue' | 'officers' | 'policy'>('settings');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Event State
  const [eventData, setEventData] = useState<EventData>({
    id: '',
    name: '',
    venue: '',
    date: '',
    status: 'active',
  });

  // Venue State (Zones & Gates)
  const [zones, setZones] = useState<ZoneData[]>([]);
  const [gates, setGates] = useState<GateData[]>([]);
  const [newZoneName, setNewZoneName] = useState('');
  const [newZoneCapacity, setNewZoneCapacity] = useState(5000);

  const [newGateName, setNewGateName] = useState('');
  const [newGateType, setNewGateType] = useState<'entry' | 'exit' | 'emergency'>('entry');
  const [newGateCapacity, setNewGateCapacity] = useState(500);
  const [newGateZoneId, setNewGateZoneId] = useState('z-1');

  // Officers State
  const [officers, setOfficers] = useState<any[]>([]);
  const [selectedOfficerId, setSelectedOfficerId] = useState('');
  const [assignZoneId, setAssignZoneId] = useState('z-1');
  const [assignTask, setAssignTask] = useState('Patrol and monitor queue pressure');

  // Notification Policy State
  const [policy, setPolicy] = useState<Record<string, NotificationPolicyRule>>({
    LOW: { risk_range: '0 - 39', inform_citizen: false, notify_operator: false, require_operator_approval: false, description: 'Normal telemetry monitoring; no proactive alerts.' },
    MEDIUM: { risk_range: '40 - 59', inform_citizen: false, notify_operator: true, require_operator_approval: true, description: 'Notify operator dashboard; require manual approval.' },
    HIGH: { risk_range: '60 - 74', inform_citizen: true, notify_operator: true, require_operator_approval: true, description: 'Publish citizen safety advisory; dispatch officer squad.' },
    CRITICAL: { risk_range: '75 - 100', inform_citizen: true, notify_operator: true, require_operator_approval: false, description: 'Auto-dispatch emergency gate opening and push high-priority alerts.' },
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [eventsList, overviewData, adminOfficers, currentPolicy] = await Promise.all([
        api.fetchEvents(),
        api.fetchOverviewData(),
        api.fetchAdminOfficers(),
        api.fetchNotificationPolicy(),
      ]);

      if (eventsList && eventsList.length > 0) setEventData(eventsList[0]);
      if (overviewData) {
        setZones(overviewData.zones);
        setGates(overviewData.gates);
        if (overviewData.zones.length > 0) {
          setNewGateZoneId(overviewData.zones[0].id);
          setAssignZoneId(overviewData.zones[0].id);
        }
      }
      setOfficers(adminOfficers);
      if (currentPolicy) setPolicy(currentPolicy);
    } catch (err) {
      console.error('Error loading Event Admin data:', err);
    } finally {
      setLoading(false);
    }
  }

  function showNotification(msg: string) {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  }

  // Save Event Settings
  async function handleSaveEventSettings() {
    setSaving(true);
    await api.updateEvent(eventData.id, eventData);
    setSaving(false);
    showNotification('Event Settings updated successfully.');
  }

  // Zone CRUD Actions
  async function handleAddZone() {
    if (!newZoneName) return;
    setSaving(true);
    const created = await api.createZone({ name: newZoneName, capacity: newZoneCapacity, event_id: eventData.id });
    setZones([...zones, created]);
    setNewZoneName('');
    setSaving(false);
    showNotification(`Safety Zone '${created.name}' created.`);
  }

  async function handleDeleteZone(id: string) {
    await api.deleteZone(id);
    setZones(zones.filter((z) => z.id !== id));
    showNotification('Safety Zone deleted.');
  }

  // Gate CRUD Actions
  async function handleAddGate() {
    if (!newGateName) return;
    setSaving(true);
    const created = await api.createGate({
      name: newGateName,
      type: newGateType,
      capacity_per_min: newGateCapacity,
      zone_id: newGateZoneId,
    });
    setGates([...gates, created]);
    setNewGateName('');
    setSaving(false);
    showNotification(`Gate '${created.name}' registered.`);
  }

  async function handleDeleteGate(id: string) {
    await api.deleteGate(id);
    setGates(gates.filter((g) => g.id !== id));
    showNotification('Gate removed from configuration.');
  }

  // Officer Assignment
  async function handleAssignOfficer() {
    if (!selectedOfficerId) return;
    setSaving(true);
    await api.assignOfficer({ officer_id: selectedOfficerId, zone_id: assignZoneId, task_description: assignTask });
    setSaving(false);
    loadData();
    showNotification('Officer assignment dispatched and updated.');
  }

  // Policy Config Save
  async function handleSavePolicy() {
    setSaving(true);
    await api.updateNotificationPolicy(policy);
    setSaving(false);
    showNotification('Notification Policy rules saved to AI Engine config.');
  }

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center space-y-4 text-slate-400">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium">Loading Event Administrator Configuration...</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <Link
              href="/overview"
              className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition flex items-center gap-1.5 text-xs font-bold"
              title="Return to Overview Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Back</span>
            </Link>
            <div className="p-2.5 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-400">
              <Sliders className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-white">Event Administrator Module</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Configure event metadata, venue layout zones, choke-point gates, officer rosters, and AI notification policies.
              </p>
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center space-x-3">
          {successMsg && (
            <div className="px-3.5 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center space-x-2 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>{successMsg}</span>
            </div>
          )}
          <div className="px-3 py-1.5 rounded-xl bg-purple-950/60 border border-purple-800/60 text-purple-300 text-xs font-semibold flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
            <span>ROLE: EVENT ADMIN</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        <button
          onClick={() => setActiveTab('settings')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'settings'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Event Settings</span>
        </button>

        <button
          onClick={() => setActiveTab('venue')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'venue'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Venue Configuration (Zones & Gates)</span>
        </button>

        <button
          onClick={() => setActiveTab('officers')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'officers'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Officer Management</span>
        </button>

        <button
          onClick={() => setActiveTab('policy')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'policy'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>Notification Policy Config</span>
        </button>
      </div>

      {/* TAB 1: EVENT SETTINGS */}
      {activeTab === 'settings' && (
        <div className="card-command p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-white">Event Operational Settings</h2>
              <p className="text-xs text-slate-400">Configure core festival metadata and operational state.</p>
            </div>
            <button
              onClick={handleSaveEventSettings}
              disabled={saving}
              className="btn-primary flex items-center space-x-2 px-4 py-2 text-xs"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300">Event Title</label>
              <input
                type="text"
                value={eventData.name}
                onChange={(e) => setEventData({ ...eventData, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300">Venue Location</label>
              <input
                type="text"
                value={eventData.venue}
                onChange={(e) => setEventData({ ...eventData, venue: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300">Event Start Timestamp</label>
              <input
                type="text"
                value={eventData.date}
                onChange={(e) => setEventData({ ...eventData, date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white font-mono-nums focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300">Operational Status</label>
              <div className="flex items-center space-x-3 pt-1">
                {(['upcoming', 'active', 'paused', 'completed'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setEventData({ ...eventData, status: st })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase transition ${
                      eventData.status === st
                        ? 'bg-purple-600 text-white shadow-md'
                        : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: VENUE CONFIGURATION */}
      {activeTab === 'venue' && (
        <div className="space-y-8">
          {/* ZONES CRUD */}
          <div className="card-command p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                  <Layers className="w-5 h-5 text-purple-400" />
                  <span>Safety Zones Configuration</span>
                </h2>
                <p className="text-xs text-slate-400">Define sector boundaries, floor area calibrations, and 4-point homography transformations.</p>
              </div>
            </div>

            {/* Add Zone Form */}
            <div className="flex flex-wrap items-end gap-4 p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Zone Name</label>
                <input
                  type="text"
                  placeholder="e.g. West Concourse Sector E"
                  value={newZoneName}
                  onChange={(e) => setNewZoneName(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Capacity (peds)</label>
                <input
                  type="number"
                  value={newZoneCapacity}
                  onChange={(e) => setNewZoneCapacity(Number(e.target.value))}
                  className="w-28 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white font-mono-nums focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Floor Area (m²)</label>
                <input
                  type="number"
                  defaultValue={500}
                  className="w-28 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white font-mono-nums focus:outline-none focus:border-purple-500"
                />
              </div>

              <button
                onClick={handleAddZone}
                disabled={!newZoneName || saving}
                className="btn-primary flex items-center space-x-2 px-4 py-1.5 text-xs font-bold"
              >
                <Plus className="w-4 h-4" />
                <span>Add Safety Zone</span>
              </button>
            </div>

            {/* Zones Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase">
                    <th className="py-2.5 px-3">Zone ID</th>
                    <th className="py-2.5 px-3">Sector Name</th>
                    <th className="py-2.5 px-3">Max Capacity</th>
                    <th className="py-2.5 px-3">Camera Calibration</th>
                    <th className="py-2.5 px-3">Current Density</th>
                    <th className="py-2.5 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                  {zones.map((z, idx) => {
                    const isCalibrated = idx % 2 === 0;
                    const calibType = idx === 0 ? 'HOMOGRAPHY (4-PT)' : isCalibrated ? 'AREA-ONLY (500m²)' : 'UNCALIBRATED';
                    return (
                      <tr key={z.id} className="hover:bg-slate-800/30">
                        <td className="py-3 px-3 font-mono-nums text-purple-400 font-bold">{z.id}</td>
                        <td className="py-3 px-3 text-white font-semibold">{z.name}</td>
                        <td className="py-3 px-3 text-slate-300 font-mono-nums">{z.capacity.toLocaleString()} peds</td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              calibType.includes('HOMOGRAPHY')
                                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                                : calibType.includes('AREA')
                                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            {calibType}
                          </span>
                          {!isCalibrated && (
                            <p className="text-[10px] text-amber-400 mt-1 flex items-center space-x-1 font-mono-nums">
                              <AlertTriangle className="w-3 h-3 inline mr-1" />
                              <span>Degraded confidence (0.70 cap)</span>
                            </p>
                          )}
                        </td>
                        <td className="py-3 px-3 text-slate-400 font-mono-nums">{Math.round((z.current_density || 0.5) * 100)}%</td>
                        <td className="py-3 px-3">
                          <button
                            onClick={() => handleDeleteZone(z.id)}
                            className="p-1.5 text-rose-400 hover:bg-rose-500/20 rounded-lg transition"
                            title="Delete Zone"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* GATES CRUD */}
          <div className="card-command p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                  <DoorClosed className="w-5 h-5 text-purple-400" />
                  <span>Gates & Choke-Points Configuration</span>
                </h2>
                <p className="text-xs text-slate-400">Configure entry turnstiles, exit pathways, and emergency escape gates.</p>
              </div>
            </div>

            {/* Add Gate Form */}
            <div className="flex flex-wrap items-end gap-4 p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Gate Name</label>
                <input
                  type="text"
                  placeholder="e.g. Emergency Exit Gate 5"
                  value={newGateName}
                  onChange={(e) => setNewGateName(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Gate Type</label>
                <select
                  value={newGateType}
                  onChange={(e) => setNewGateType(e.target.value as any)}
                  className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="entry">ENTRY (Ingress)</option>
                  <option value="exit">EXIT (Egress)</option>
                  <option value="emergency">EMERGENCY (Choke-point)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Associated Zone</label>
                <select
                  value={newGateZoneId}
                  onChange={(e) => setNewGateZoneId(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500 font-mono-nums"
                >
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name} ({z.id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Flow Cap (p/min)</label>
                <input
                  type="number"
                  value={newGateCapacity}
                  onChange={(e) => setNewGateCapacity(Number(e.target.value))}
                  className="w-28 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white font-mono-nums focus:outline-none focus:border-purple-500"
                />
              </div>

              <button
                onClick={handleAddGate}
                disabled={!newGateName || saving}
                className="btn-primary flex items-center space-x-2 px-4 py-1.5 text-xs font-bold"
              >
                <Plus className="w-4 h-4" />
                <span>Register Gate</span>
              </button>
            </div>

            {/* Gates Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase">
                    <th className="py-2.5 px-3">Gate ID</th>
                    <th className="py-2.5 px-3">Gate Name</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Associated Zone</th>
                    <th className="py-2.5 px-3">Capacity</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                  {gates.map((g) => (
                    <tr key={g.id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-3 font-mono-nums text-purple-400 font-bold">{g.id}</td>
                      <td className="py-3 px-3 text-white font-semibold">{g.name}</td>
                      <td className="py-3 px-3 uppercase font-bold text-[10px] text-slate-300">
                        <span className={`px-2 py-0.5 rounded ${g.type === 'emergency' ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-800 text-slate-300'}`}>
                          {g.type}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-400 font-mono-nums">{g.zone_id}</td>
                      <td className="py-3 px-3 text-slate-300 font-mono-nums">{g.capacity_per_min || 500} p/min</td>
                      <td className="py-3 px-3 uppercase font-bold text-[10px]">
                        <span className={`px-2 py-0.5 rounded ${g.status === 'open' ? 'bg-emerald-500/20 text-emerald-300' : g.status === 'restricted' ? 'bg-amber-500/20 text-amber-300' : 'bg-rose-500/20 text-rose-300'}`}>
                          {g.status}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <button
                          onClick={() => handleDeleteGate(g.id)}
                          className="p-1.5 text-rose-400 hover:bg-rose-500/20 rounded-lg transition"
                          title="Remove Gate"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: OFFICER MANAGEMENT */}
      {activeTab === 'officers' && (
        <div className="card-command p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                <Users className="w-5 h-5 text-purple-400" />
                <span>Field Officer Squad Assignment & Roster</span>
              </h2>
              <p className="text-xs text-slate-400">Assign ground officers to active festival sectors and manage availability.</p>
            </div>
          </div>

          {/* Officer Assignment Panel */}
          <div className="flex flex-wrap items-end gap-4 p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400">Select Field Officer</label>
              <select
                value={selectedOfficerId}
                onChange={(e) => setSelectedOfficerId(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
              >
                <option value="">-- Choose Officer --</option>
                {officers.map((off) => (
                  <option key={off.id} value={off.id}>
                    {off.name} ({off.availability})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400">Target Zone</label>
              <select
                value={assignZoneId}
                onChange={(e) => setAssignZoneId(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500 font-mono-nums"
              >
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1 flex-1">
              <label className="text-[11px] font-bold text-slate-400">Task Instruction</label>
              <input
                type="text"
                value={assignTask}
                onChange={(e) => setAssignTask(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              onClick={handleAssignOfficer}
              disabled={!selectedOfficerId || saving}
              className="btn-primary flex items-center space-x-2 px-4 py-1.5 text-xs font-bold"
            >
              <Plus className="w-4 h-4" />
              <span>Dispatch Assignment</span>
            </button>
          </div>

          {/* Officers Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Officer Name</th>
                  <th className="py-2.5 px-3">Email</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Assigned Task</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                {officers.map((off) => (
                  <tr key={off.id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 text-white font-semibold">{off.name}</td>
                    <td className="py-3 px-3 text-slate-400 font-mono-nums">{off.email || 'N/A'}</td>
                    <td className="py-3 px-3 uppercase font-bold text-[10px]">
                      <span className={`px-2 py-0.5 rounded ${off.availability === 'assigned' ? 'bg-purple-500/20 text-purple-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
                        {off.availability}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-300">
                      {off.current_assignment?.task_description || 'Standby for dispatch'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: NOTIFICATION POLICY CONFIG */}
      {activeTab === 'policy' && (
        <div className="card-command p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                <Bell className="w-5 h-5 text-purple-400" />
                <span>AI Recommendation Notification Policy Configuration</span>
              </h2>
              <p className="text-xs text-slate-400">
                Rule matrix mapping risk levels to notification behavior (stored as JSON configuration read directly by the AI engine).
              </p>
            </div>

            <button
              onClick={handleSavePolicy}
              disabled={saving}
              className="btn-primary flex items-center space-x-2 px-4 py-2 text-xs"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saving Policy...' : 'Save Policy JSON'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {Object.entries(policy).map(([lvl, rule]) => (
              <div key={lvl} className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span
                      className={`px-3 py-1 rounded-lg text-xs font-extrabold uppercase font-mono-nums ${
                        lvl === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : lvl === 'HIGH'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : lvl === 'MEDIUM'
                          ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {lvl} RISK ({rule.risk_range})
                    </span>
                    <span className="text-xs text-slate-400">{rule.description}</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <label className="flex items-center space-x-3 p-2.5 bg-slate-900 border border-slate-800 rounded-lg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rule.inform_citizen}
                      onChange={(e) =>
                        setPolicy({
                          ...policy,
                          [lvl]: { ...rule, inform_citizen: e.target.checked },
                        })
                      }
                      className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                    />
                    <span className="text-xs text-slate-200 font-semibold">Inform Citizen (Push Advisory)</span>
                  </label>

                  <label className="flex items-center space-x-3 p-2.5 bg-slate-900 border border-slate-800 rounded-lg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rule.notify_operator}
                      onChange={(e) =>
                        setPolicy({
                          ...policy,
                          [lvl]: { ...rule, notify_operator: e.target.checked },
                        })
                      }
                      className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                    />
                    <span className="text-xs text-slate-200 font-semibold">Notify Operator Dashboard</span>
                  </label>

                  <label className="flex items-center space-x-3 p-2.5 bg-slate-900 border border-slate-800 rounded-lg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rule.require_operator_approval}
                      onChange={(e) =>
                        setPolicy({
                          ...policy,
                          [lvl]: { ...rule, require_operator_approval: e.target.checked },
                        })
                      }
                      className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                    />
                    <span className="text-xs text-slate-200 font-semibold">Require Manual Operator Approval</span>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
