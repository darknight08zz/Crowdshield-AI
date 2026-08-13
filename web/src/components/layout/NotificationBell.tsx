'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Bell, AlertTriangle, CheckCircle2, ShieldAlert, X, ExternalLink, Info } from 'lucide-react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { api } from '@/lib/api';

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'INFO';
  timestamp: string;
  read: boolean;
  link: string;
}

export function NotificationBell() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Initial fetch & Realtime subscription
  useEffect(() => {
    let isSubscribed = true;

    async function loadInitialData() {
      try {
        const incidents = await api.fetchIncidents();
        if (isSubscribed && incidents && incidents.length > 0) {
          const initialItems: NotificationItem[] = incidents.slice(0, 10).map((inc) => ({
            id: inc.id || `inc-${Math.random()}`,
            title: `INCIDENT: ${inc.type || inc.location_name || 'Alert Reported'}`,
            message: inc.description || `Location: ${inc.location_name || 'Sector'} | Status: ${inc.status || 'Pending'}`,
            severity: inc.status === 'pending' ? 'HIGH' : 'MODERATE',
            timestamp: inc.created_at ? new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recently',
            read: false,
            link: '/incidents',
          }));
          setNotifications(initialItems);
        }
      } catch (e) {
        // Fallback silently if API offline
      }
    }

    loadInitialData();

    // Connect Supabase Realtime CDC Channel
    const supabase = createClient();
    const channel = supabase
      .channel('header-notifications-cdc')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'incidents' },
        (payload) => {
          const newRow = payload.new;
          if (newRow && isSubscribed) {
            const newItem: NotificationItem = {
              id: newRow.id || `inc-${Date.now()}`,
              title: `REALTIME INCIDENT: ${newRow.type || 'Critical Alert'}`,
              message: newRow.description || `Location: ${newRow.location_name || 'Sector'}`,
              severity: 'CRITICAL',
              timestamp: 'Just now',
              read: false,
              link: '/incidents',
            };
            setNotifications((prev) => [newItem, ...prev]);
          }
        }
      )
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'ai_recommendations' },
        (payload) => {
          const newRow = payload.new;
          if (newRow && isSubscribed) {
            const newItem: NotificationItem = {
              id: newRow.id || `rec-${Date.now()}`,
              title: `AI RECOMMENDATION DISPATCHED`,
              message: newRow.action_type ? `Action: ${newRow.action_type}` : 'New AI intervention ready for review',
              severity: 'MODERATE',
              timestamp: 'Just now',
              read: false,
              link: '/verify',
            };
            setNotifications((prev) => [newItem, ...prev]);
          }
        }
      )
      .subscribe();

    // 10-Second Polling Sync Fallback
    const pollInterval = setInterval(async () => {
      try {
        const latestIncidents = await api.fetchIncidents();
        if (isSubscribed && latestIncidents && latestIncidents.length > 0) {
          setNotifications((prev) => {
            const existingIds = new Set(prev.map((n) => n.id));
            const newFetched: NotificationItem[] = [];
            for (const inc of latestIncidents.slice(0, 5)) {
              if (inc.id && !existingIds.has(inc.id)) {
                newFetched.push({
                  id: inc.id,
                  title: `INCIDENT: ${inc.type || inc.location_name || 'Alert Reported'}`,
                  message: inc.description || `Location: ${inc.location_name || 'Sector'}`,
                  severity: inc.status === 'pending' ? 'HIGH' : 'MODERATE',
                  timestamp: 'Recently',
                  read: false,
                  link: '/incidents',
                });
              }
            }
            return newFetched.length > 0 ? [...newFetched, ...prev] : prev;
          });
        }
      } catch (e) {
        // Polling retry
      }
    }, 10000);

    return () => {
      isSubscribed = false;
      supabase.removeChannel(channel);
      clearInterval(pollInterval);
    };
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markAsRead = (id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    setIsOpen(false);
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'MODERATE':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button with Unread Badge */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl bg-slate-950/80 hover:bg-slate-800 border border-slate-800 transition text-slate-400 hover:text-white focus:outline-none"
        title="Notifications & System Alerts"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white shadow-lg animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notifications Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-3 w-80 sm:w-96 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-slate-800 shadow-2xl z-50 overflow-hidden animate-fadeIn">
          {/* Header Bar */}
          <div className="p-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-cyan-400" />
              <span className="font-extrabold text-xs text-white uppercase tracking-wider">
                SYSTEM NOTIFICATIONS
              </span>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[10px] font-bold font-mono-nums">
                  {unreadCount} UNREAD
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-[10px] font-bold text-cyan-400 hover:text-cyan-300 transition"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
            {notifications.length === 0 ? (
              <div className="p-8 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto opacity-80" />
                <p className="text-xs text-slate-300 font-semibold">System Status Normal</p>
                <p className="text-[11px] text-slate-500">No active critical alerts or unread notifications.</p>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`p-3.5 transition flex items-start justify-between gap-3 ${
                    item.read ? 'bg-slate-950/30 opacity-70' : 'bg-slate-900/80 hover:bg-slate-850'
                  }`}
                >
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 text-[9px] font-black rounded border uppercase ${getSeverityBadge(item.severity)}`}>
                        {item.severity}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono-nums">{item.timestamp}</span>
                    </div>
                    <div className="text-xs font-bold text-slate-200">{item.title}</div>
                    <div className="text-[11px] text-slate-400 leading-snug">{item.message}</div>
                  </div>

                  <Link
                    href={item.link}
                    onClick={() => markAsRead(item.id)}
                    className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/40 transition flex-shrink-0"
                    title="View Alert Location"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ))
            )}
          </div>

          {/* Footer Bar */}
          <div className="p-2.5 border-t border-slate-800 bg-slate-950/80 text-center">
            <Link
              href="/incidents"
              onClick={() => setIsOpen(false)}
              className="text-xs font-bold text-slate-400 hover:text-cyan-400 transition inline-flex items-center gap-1"
            >
              View Full Incident Stream &rarr;
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
