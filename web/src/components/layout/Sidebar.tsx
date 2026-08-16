'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Target, AlertTriangle, Users, CheckCircle2, Sliders, ShieldCheck, TrendingUp, UserCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const pathname = usePathname();

  const mainNavItems = [
    { label: 'Overview', href: '/overview', icon: LayoutDashboard },
    { label: 'Zone Detail & AI', href: '/zones/z-1', icon: Target },
    { label: 'Trend Analytics', href: '/analytics', icon: TrendingUp },
    { label: 'Incidents Stream', href: '/incidents', icon: AlertTriangle, badge: '2' },
    { label: 'Field Response Action', href: '/field', icon: UserCheck },
    { label: 'Field Officers', href: '/officers', icon: Users },
    { label: 'Verify & Results', href: '/verify', icon: CheckCircle2 },
  ];


  const adminNavItems = [
    { label: 'Event Administrator', href: '/admin/event', icon: Sliders },
    { label: 'System Administrator', href: '/admin/system', icon: ShieldCheck },
  ];

  return (
    <aside className="w-64 bg-slate-950/90 border-r border-slate-800/80 p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-6">
        <div>
          <div className="px-3 py-2 text-[11px] font-bold text-slate-500 tracking-wider uppercase">
            OPERATIONAL MODULES
          </div>

          <nav className="space-y-1.5 mt-1">
            {mainNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname.startsWith(item.href) && (item.href !== '/overview' || pathname === '/overview');

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    'flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition group',
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-950/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  )}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={cn('w-4 h-4', isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200')} />
                    <span>{item.label}</span>
                  </div>

                  {item.badge && (
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div>
          <div className="px-3 py-2 text-[11px] font-bold text-slate-500 tracking-wider uppercase">
            ADMINISTRATION
          </div>

          <nav className="space-y-1.5 mt-1">
            {adminNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname.startsWith(item.href);

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    'flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition group',
                    isActive
                      ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30 shadow-lg shadow-purple-950/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  )}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={cn('w-4 h-4', isActive ? 'text-purple-400' : 'text-slate-400 group-hover:text-slate-200')} />
                    <span>{item.label}</span>
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Control Room Operational Status Footer */}
      <div className="p-3 bg-slate-900/70 rounded-xl border border-slate-800 text-xs space-y-1.5">
        <div className="text-[11px] font-bold text-slate-400 flex items-center justify-between">
          <span>AI RISK MODEL</span>
          <span className="text-emerald-400">XGBoost R² 0.98</span>
        </div>
        <div className="text-[10px] text-slate-500">
          Last feature cycle: <span className="text-slate-300">12s ago</span>
        </div>
      </div>
    </aside>
  );
}
