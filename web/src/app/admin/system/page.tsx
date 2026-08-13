'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShieldCheck,
  Activity,
  Users,
  Lock,
  Search,
  RefreshCw,
  CheckCircle2,
  FileText,
  KeyRound,
  UserCheck,
  Eye,
  Server,
  Database,
  Cpu,
  BellRing,
  UserPlus,
  Mail,
  Copy,
  Check,
  ArrowLeft,
} from 'lucide-react';
import {
  api,
  UserData,
  RbacMatrixItem,
  SystemHealthData,
  AuditLogData
} from '@/lib/api';

export default function SystemAdminPage() {
  const [activeTab, setActiveTab] = useState<'health' | 'users' | 'rbac' | 'audit'>('health');
  const [loading, setLoading] = useState(true);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // System Health State
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);

  // User Management State
  const [users, setUsers] = useState<UserData[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('');

  // Staff Invite Modal State
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteName, setInviteName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'event_admin' | 'operator' | 'field_officer'>('operator');
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [isInviting, setIsInviting] = useState(false);
  const [createdInviteLink, setCreatedInviteLink] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // RBAC Matrix State
  const [rbacItems, setRbacItems] = useState<RbacMatrixItem[]>([]);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLogData[]>([]);
  const [auditSearch, setAuditSearch] = useState('');
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLogData | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  async function loadAllData() {
    setLoading(true);
    try {
      const [hData, uData, rData, aData] = await Promise.all([
        api.fetchSystemHealth(),
        api.fetchAdminUsers(),
        api.fetchRbacMatrix(),
        api.fetchSearchableAuditLogs(),
      ]);

      setHealthData(hData);
      setUsers(uData);
      setRbacItems(rData);
      setAuditLogs(aData);
    } catch (err) {
      console.error('Error loading System Admin data:', err);
    } finally {
      setLoading(false);
    }
  }

  function showNotification(msg: string) {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  }

  // Handle Staff Invitation Submission
  async function handleInviteSubmit(e: React.FormEvent) {
    e.preventDefault();
    setInviteError(null);
    setIsInviting(true);
    setCreatedInviteLink(null);

    try {
      const result = await api.inviteStaffUser({
        name: inviteName,
        email: inviteEmail,
        role: inviteRole,
      });

      setCreatedInviteLink(result.invite_link);
      showNotification(`Staff invitation created for ${inviteEmail}.`);

      // Refresh users table
      const updatedUsers = await api.fetchAdminUsers();
      setUsers(updatedUsers);
    } catch (err: any) {
      setInviteError(err.message || 'Failed to dispatch staff invitation.');
    } finally {
      setIsInviting(false);
    }
  }

  function copyInviteLink() {
    if (createdInviteLink) {
      navigator.clipboard.writeText(createdInviteLink);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 3000);
    }
  }

  // User Role Update
  async function handleRoleChange(userId: string, newRole: string) {
    await api.updateUserRole(userId, newRole);
    setUsers(users.map((u) => (u.id === userId ? { ...u, role: newRole as any } : u)));
    showNotification(`User role updated to '${newRole}' via Supabase Auth Admin.`);
  }

  // Toggle User Status
  async function handleToggleStatus(userId: string, currentStatus: boolean) {
    const nextStatus = !currentStatus;
    await api.toggleUserStatus(userId, nextStatus);
    setUsers(users.map((u) => (u.id === userId ? { ...u, is_active: nextStatus } : u)));
    showNotification(`User account ${nextStatus ? 'enabled' : 'disabled'}.`);
  }

  // Password Reset Trigger
  async function handleResetPassword(userId: string) {
    const res = await api.resetUserPassword(userId);
    showNotification(res.message || 'Password reset link sent to user email.');
  }

  // Search Audit Logs
  async function handleAuditSearch(q: string) {
    setAuditSearch(q);
    const results = await api.fetchSearchableAuditLogs(q);
    setAuditLogs(results);
  }

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center space-y-4 text-slate-400">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium">Loading System Administrator Console...</p>
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
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-white">System Administrator Module</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Monitor system health, manage platform users via backend Supabase Auth API, view dynamic RBAC declarations, and inspect audit logs.
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
            <span>ROLE: SYSTEM ADMIN</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        <button
          onClick={() => setActiveTab('health')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'health'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>System Health Probes</span>
        </button>

        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'users'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>User Management (Supabase Auth)</span>
        </button>

        <button
          onClick={() => setActiveTab('rbac')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'rbac'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Lock className="w-4 h-4" />
          <span>Dynamic RBAC Matrix</span>
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center space-x-2 px-4 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'audit'
              ? 'border-purple-500 text-purple-400 bg-purple-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Audit Log Viewer</span>
        </button>
      </div>

      {/* TAB 1: SYSTEM HEALTH PROBES */}
      {activeTab === 'health' && healthData && (
        <div className="space-y-6">
          <div className="flex items-center justify-between card-command p-6">
            <div>
              <div className="text-xs font-bold text-slate-400 uppercase">OVERALL SYSTEM INFRASTRUCTURE STATUS</div>
              <div className="text-xl font-extrabold text-white mt-1 flex items-center space-x-3">
                <span className={`w-3.5 h-3.5 rounded-full ${healthData.overall_status === 'healthy' ? 'bg-emerald-400 shadow-lg shadow-emerald-950' : 'bg-amber-400'}`} />
                <span className="uppercase">{healthData.overall_status} (ALL SERVICES OPERATIONAL)</span>
              </div>
            </div>
            <button
              onClick={loadAllData}
              className="btn-secondary text-xs py-2 px-4 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Refresh Probes</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* API Health */}
            <div className="p-6 card-command space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
                    <Server className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{healthData.services.api.name}</h3>
                    <p className="text-[11px] text-slate-400">FastAPI REST Core Engine</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-extrabold uppercase border border-emerald-500/30">
                  {healthData.services.api.status}
                </span>
              </div>
              <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800 font-mono-nums">
                {healthData.services.api.detail}
              </p>
            </div>

            {/* Database Health */}
            <div className="p-6 card-command space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{healthData.services.database.name}</h3>
                    <p className="text-[11px] text-slate-400">PostgreSQL / Supabase Engine</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-extrabold uppercase border border-emerald-500/30">
                  {healthData.services.database.status}
                </span>
              </div>
              <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800 font-mono-nums">
                {healthData.services.database.detail}
              </p>
            </div>

            {/* AI Risk Engine Health */}
            <div className="p-6 card-command space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{healthData.services.ai_engine.name}</h3>
                    <p className="text-[11px] text-slate-400">XGBoost Feature & Inference Pipeline</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-extrabold uppercase border border-emerald-500/30">
                  {healthData.services.ai_engine.status}
                </span>
              </div>
              <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800 font-mono-nums">
                {healthData.services.ai_engine.detail}
              </p>
            </div>

            {/* Push Notification Service Health */}
            <div className="p-6 card-command space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
                    <BellRing className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{healthData.services.notifications.name}</h3>
                    <p className="text-[11px] text-slate-400">Firebase Cloud Messaging (FCM)</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-extrabold uppercase border border-emerald-500/30">
                  {healthData.services.notifications.status}
                </span>
              </div>
              <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800 font-mono-nums">
                {healthData.services.notifications.detail}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: USER MANAGEMENT */}
      {activeTab === 'users' && (
        <div className="card-command p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                <Users className="w-5 h-5 text-purple-400" />
                <span>Platform User Administration</span>
              </h2>
              <p className="text-xs text-slate-400">
                Provision new staff members via invite links, update roles, and manage account statuses.
              </p>
            </div>

            <div className="flex items-center space-x-3">
              {/* Invite User Button */}
              <button
                onClick={() => {
                  setInviteName('');
                  setInviteEmail('');
                  setCreatedInviteLink(null);
                  setInviteError(null);
                  setIsInviteModalOpen(true);
                }}
                className="btn-primary flex items-center space-x-2 px-4 py-2 text-xs font-bold"
              >
                <UserPlus className="w-4 h-4" />
                <span>Invite Staff Member</span>
              </button>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search user name or email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500 w-56"
                />
              </div>

              <select
                value={userRoleFilter}
                onChange={(e) => setUserRoleFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
              >
                <option value="">All Roles</option>
                <option value="system_admin">system_admin</option>
                <option value="event_admin">event_admin</option>
                <option value="operator">operator</option>
                <option value="field_officer">field_officer</option>
                <option value="citizen">citizen</option>
              </select>
            </div>
          </div>

          {/* Users Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase">
                  <th className="py-2.5 px-3">User Name</th>
                  <th className="py-2.5 px-3">Email Address</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Account Status</th>
                  <th className="py-2.5 px-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                {users
                  .filter((u) => !userRoleFilter || u.role === userRoleFilter)
                  .filter((u) => !userSearch || u.name.toLowerCase().includes(userSearch.toLowerCase()) || u.email.toLowerCase().includes(userSearch.toLowerCase()))
                  .map((u) => (
                    <tr key={u.id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-3 text-white font-semibold">{u.name}</td>
                      <td className="py-3 px-3 text-slate-400 font-mono-nums">{u.email}</td>
                      <td className="py-3 px-3 font-mono-nums">
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          className="bg-slate-950 border border-slate-800 text-purple-300 rounded-lg px-2.5 py-1 text-xs font-bold focus:outline-none focus:border-purple-500"
                        >
                          <option value="citizen">citizen</option>
                          <option value="field_officer">field_officer</option>
                          <option value="operator">operator</option>
                          <option value="event_admin">event_admin</option>
                          <option value="system_admin">system_admin</option>
                        </select>
                      </td>
                      <td className="py-3 px-3">
                        <button
                          onClick={() => handleToggleStatus(u.id, u.is_active)}
                          className={`px-3 py-1 rounded-full text-[10px] font-extrabold uppercase flex items-center space-x-1.5 transition ${
                            u.is_active ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-rose-500/20 hover:text-rose-300' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-emerald-500/20 hover:text-emerald-300'
                          }`}
                        >
                          {u.is_active ? <UserCheck className="w-3.5 h-3.5" /> : <Mail className="w-3.5 h-3.5" />}
                          <span>{u.is_active ? 'Active' : 'Pending / Disabled'}</span>
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <button
                          onClick={() => handleResetPassword(u.id)}
                          className="btn-secondary text-xs py-1 px-3 flex items-center space-x-1.5"
                          title="Trigger Password Reset"
                        >
                          <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                          <span>Reset Access</span>
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {/* STAFF INVITATION MODAL */}
          {isInviteModalOpen && (
            <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
              <div className="card-command max-w-md w-full p-6 space-y-5 shadow-2xl relative">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <UserPlus className="w-5 h-5 text-purple-400" />
                    <h3 className="text-base font-extrabold text-white">Invite New Staff Member</h3>
                  </div>
                  <button
                    onClick={() => setIsInviteModalOpen(false)}
                    className="text-slate-400 hover:text-white font-bold"
                  >
                    ✕
                  </button>
                </div>

                {inviteError && (
                  <div className="bg-rose-950/80 border border-rose-500/40 text-rose-300 p-3 rounded-xl text-xs font-semibold">
                    {inviteError}
                  </div>
                )}

                {createdInviteLink ? (
                  <div className="space-y-4 bg-emerald-950/40 border border-emerald-500/30 p-4 rounded-xl">
                    <div className="flex items-center space-x-2 text-emerald-300 text-xs font-bold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Staff Invitation Created Successfully!</span>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-400 font-semibold uppercase">Unique Activation Link:</label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          readOnly
                          value={createdInviteLink}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-cyan-300 font-mono-nums focus:outline-none"
                        />
                        <button
                          onClick={copyInviteLink}
                          className="btn-primary text-xs py-1.5 px-3 shrink-0 flex items-center space-x-1"
                        >
                          {copiedLink ? <Check className="w-4 h-4 text-white" /> : <Copy className="w-4 h-4" />}
                          <span>{copiedLink ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Share this activation link with <strong className="text-white">{inviteEmail}</strong>. They will set their password and activate their staff account with the pre-assigned role <strong className="text-purple-300 uppercase">{inviteRole}</strong>.
                    </p>

                    <button
                      onClick={() => {
                        setCreatedInviteLink(null);
                        setInviteName('');
                        setInviteEmail('');
                      }}
                      className="btn-secondary w-full py-2 text-xs"
                    >
                      Invite Another Staff Member
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleInviteSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                        Full Name
                      </label>
                      <input
                        type="text"
                        required
                        value={inviteName}
                        onChange={(e) => setInviteName(e.target.value)}
                        placeholder="Officer Alex Morgan"
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                        Official Email Address
                      </label>
                      <input
                        type="email"
                        required
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="alex.morgan@crowdshield.gov"
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
                        Assigned Staff Role
                      </label>
                      <select
                        value={inviteRole}
                        onChange={(e) => setInviteRole(e.target.value as any)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-purple-300 font-bold focus:outline-none focus:border-purple-500"
                      >
                        <option value="operator">Control-Room Operator (operator)</option>
                        <option value="event_admin">Event Administrator (event_admin)</option>
                        <option value="field_officer">Field Officer (field_officer)</option>
                      </select>
                      <p className="text-[10px] text-slate-500 mt-1 font-sans">
                        * Note: System Administrator and Citizen roles cannot be invited via UI per security architecture.
                      </p>
                    </div>

                    <div className="flex justify-end space-x-3 pt-2">
                      <button
                        type="button"
                        onClick={() => setIsInviteModalOpen(false)}
                        className="btn-secondary text-xs py-2 px-4"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={isInviting}
                        className="btn-primary text-xs py-2 px-4 disabled:opacity-50"
                      >
                        {isInviting ? 'Generating Invitation...' : 'Send Staff Invite'}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: DYNAMIC RBAC MATRIX */}
      {activeTab === 'rbac' && (
        <div className="card-command p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                <Lock className="w-5 h-5 text-purple-400" />
                <span>Dynamic Role-Based Access Control (RBAC) Inspection Matrix</span>
              </h2>
              <p className="text-xs text-slate-400">
                Live visualization of API endpoint accessibility extracted directly from backend route dependency declarations (`require_role`).
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase">
                  <th className="py-2.5 px-3">API Endpoint Path</th>
                  <th className="py-2.5 px-3">HTTP Methods</th>
                  <th className="py-2.5 px-3">Allowed Roles</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                {rbacItems.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-mono-nums text-cyan-400 font-bold">{item.path}</td>
                    <td className="py-3 px-3 font-mono-nums text-slate-300">
                      {item.methods.map((m) => (
                        <span key={m} className="mr-1.5 px-2 py-0.5 rounded bg-slate-800 text-[10px] font-extrabold uppercase">
                          {m}
                        </span>
                      ))}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex flex-wrap gap-1.5">
                        {item.allowed_roles.map((r) => (
                          <span
                            key={r}
                            className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                              r === 'system_admin'
                                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                                : r === 'event_admin'
                                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                : r === 'operator'
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {r}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: AUDIT LOG VIEWER */}
      {activeTab === 'audit' && (
        <div className="card-command p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-extrabold text-white flex items-center space-x-2">
                <FileText className="w-5 h-5 text-purple-400" />
                <span>Forensic System Audit Log Viewer</span>
              </h2>
              <p className="text-xs text-slate-400">
                Searchable trail over the persistent audit_log table tracking actor actions and before/after state modifications.
              </p>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search action or target..."
                value={auditSearch}
                onChange={(e) => handleAuditSearch(e.target.value)}
                className="pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500 w-72 font-mono-nums"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Actor ID</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Target Resource</th>
                  <th className="py-2.5 px-3">State Data</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 text-slate-400 font-mono-nums text-[11px]">
                      {new Date(log.created_at || log.timestamp || Date.now()).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-3 text-purple-300 font-mono-nums font-bold text-[11px]">
                      {log.actor_id || log.user_email || 'System'}
                    </td>
                    <td className="py-3 px-3 text-white font-semibold">
                      <span className="px-2 py-0.5 rounded bg-slate-800 font-mono-nums text-[10px] text-amber-300">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-300 font-mono-nums">{log.target || log.target_resource}</td>
                    <td className="py-3 px-3">
                      <button
                        onClick={() => setSelectedAuditLog(log)}
                        className="btn-secondary text-[11px] py-1 px-2.5 flex items-center space-x-1.5"
                      >
                        <Eye className="w-3.5 h-3.5 text-purple-400" />
                        <span>Inspect Payload</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Inspection Modal */}
          {selectedAuditLog && (
            <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
              <div className="card-command max-w-2xl w-full p-6 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white font-mono-nums">
                    Audit Entry Inspection: {selectedAuditLog.action}
                  </h3>
                  <button
                    onClick={() => setSelectedAuditLog(null)}
                    className="text-slate-400 hover:text-white font-bold"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-3 text-xs font-mono-nums">
                  <div>
                    <span className="text-slate-400">Target:</span>{' '}
                    <span className="text-purple-300">{selectedAuditLog.target || selectedAuditLog.target_resource}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Before State:</span>
                    <pre className="p-3 bg-slate-950 rounded-xl text-slate-300 overflow-x-auto text-[11px] mt-1 border border-slate-800">
                      {JSON.stringify(selectedAuditLog.before_state || {}, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span className="text-slate-400">After State:</span>
                    <pre className="p-3 bg-slate-950 rounded-xl text-emerald-300 overflow-x-auto text-[11px] mt-1 border border-slate-800">
                      {JSON.stringify(selectedAuditLog.after_state || {}, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setSelectedAuditLog(null)}
                    className="btn-primary text-xs py-1.5 px-4"
                  >
                    Close Payload
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
