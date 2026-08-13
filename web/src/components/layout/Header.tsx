'use client';

import React, { useState, useEffect } from 'react';
import { Shield, User, AlertOctagon, LogOut } from 'lucide-react';
import { useAuth } from '@/components/providers/AuthProvider';
import { api } from '@/lib/api';
import { NotificationBell } from './NotificationBell';

export function Header() {
  const { user, logout } = useAuth();
  const [eventName, setEventName] = useState<string>('ACTIVE EVENT');

  useEffect(() => {
    async function loadEvent() {
      try {
        const events = await api.fetchEvents();
        if (events && events.length > 0 && events[0].name) {
          setEventName(events[0].name);
        }
      } catch (e) {
        // Fallback silently
      }
    }
    loadEvent();
  }, []);

  const getInitials = (name?: string) => {
    if (!name) return 'CS';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getRoleLabel = (role?: string) => {
    switch (role) {
      case 'system_admin':
        return 'SYSTEM ADMINISTRATOR';
      case 'event_admin':
        return 'EVENT ADMINISTRATOR';
      case 'operator':
        return 'COMMAND OPERATOR';
      case 'field_officer':
        return 'FIELD OFFICER';
      default:
        return 'PUBLIC CITIZEN';
    }
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Active Event Title */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="font-extrabold text-lg text-white tracking-wider">
            CROWD<span className="text-cyan-400">SHIELD</span>
          </span>
        </div>
        <div className="h-5 w-px bg-slate-800" />
        <div className="flex items-center space-x-2 bg-slate-950/60 px-3 py-1 rounded-lg border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-semibold text-slate-300">
            EVENT: <span className="text-cyan-300">{eventName}</span>
          </span>
        </div>
      </div>

      {/* Center Emergency Broadcast */}
      <div className="flex items-center space-x-4">
        <button className="bg-rose-600 hover:bg-rose-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs tracking-wide shadow-lg shadow-rose-600/30 transition flex items-center gap-1.5 active:scale-95">
          <AlertOctagon className="w-4 h-4" />
          EMERGENCY BROADCAST
        </button>
      </div>

      {/* Right User Profile & Persistent Logout Control */}
      <div className="flex items-center space-x-4">
        <NotificationBell />

        <div className="flex items-center space-x-3 bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800">
          <div className="w-7 h-7 rounded-full bg-cyan-600/30 text-cyan-400 border border-cyan-500/40 flex items-center justify-center text-xs font-bold">
            {getInitials(user?.name)}
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-slate-200">{user?.name || 'Command Staff'}</div>
            <div className="text-[10px] text-cyan-400 font-semibold tracking-wider">
              {getRoleLabel(user?.role)}
            </div>
          </div>
        </div>

        {/* Visible Logout Button */}
        <button
          onClick={logout}
          title="Sign Out of Session"
          className="p-2 rounded-xl bg-slate-950/80 hover:bg-rose-950/80 text-slate-400 hover:text-rose-300 border border-slate-800 hover:border-rose-500/40 transition flex items-center gap-1.5 text-xs font-semibold"
        >
          <LogOut className="w-4 h-4 text-rose-400" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
