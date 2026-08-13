'use client';

import React from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, ShieldAlert, ArrowLeft, LogOut } from 'lucide-react';
import { useAuth } from '@/components/providers/AuthProvider';

function UnauthorizedContent() {
  const searchParams = useSearchParams();
  const requiredRole = searchParams.get('required') || 'Elevated Access Role';
  const currentRole = searchParams.get('current') || 'Standard User';
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg bg-slate-900/80 backdrop-blur-xl border border-rose-500/30 rounded-2xl shadow-2xl p-8 z-10 relative text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-rose-950/80 border border-rose-500/50 text-rose-400 flex items-center justify-center mx-auto shadow-xl shadow-rose-900/30">
          <ShieldAlert className="w-10 h-10" />
        </div>

        <div>
          <h1 className="text-2xl font-black text-white tracking-wider">ACCESS DENIED</h1>
          <p className="text-xs text-rose-300 font-semibold uppercase tracking-widest mt-1">
            Insufficient Role Permissions
          </p>
        </div>

        <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 text-left space-y-2 text-xs">
          <div className="flex justify-between items-center py-1 border-b border-slate-800">
            <span className="text-slate-400 font-semibold">Active User Account:</span>
            <span className="font-bold text-white">{user?.email || 'Authenticated User'}</span>
          </div>
          <div className="flex justify-between items-center py-1 border-b border-slate-800">
            <span className="text-slate-400 font-semibold">Your Assigned Role:</span>
            <span className="px-2 py-0.5 bg-slate-800 text-slate-200 font-bold uppercase rounded text-[10px]">
              {user?.role || currentRole}
            </span>
          </div>
          <div className="flex justify-between items-center py-1">
            <span className="text-slate-400 font-semibold">Required Access Role:</span>
            <span className="px-2 py-0.5 bg-rose-950 text-rose-300 border border-rose-500/40 font-bold uppercase rounded text-[10px]">
              {requiredRole}
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          You do not have authorization to view this protected command surface. If you require access, contact your System Administrator to request a role elevation.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <button
            onClick={() => router.push('/overview')}
            className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold py-2.5 px-4 rounded-xl text-xs transition flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Dashboard</span>
          </button>

          <button
            onClick={logout}
            className="flex-1 bg-rose-900/60 hover:bg-rose-800/80 text-rose-200 border border-rose-500/40 font-bold py-2.5 px-4 rounded-xl text-xs transition flex items-center justify-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            <span>Switch Account</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UnauthorizedPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">Loading...</div>}>
      <UnauthorizedContent />
    </React.Suspense>
  );
}

