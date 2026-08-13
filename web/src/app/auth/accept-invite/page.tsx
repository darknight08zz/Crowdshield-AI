'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, Lock, AlertOctagon, CheckCircle2, UserCheck, ArrowRight, XCircle } from 'lucide-react';
import { API_BASE_URL } from '@/lib/constants';
import { useAuth } from '@/components/providers/AuthProvider';

function AcceptInviteContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const router = useRouter();
  const { refreshSession } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [inviteData, setInviteData] = useState<{
    valid: boolean;
    email: string;
    name: string;
    role: string;
  } | null>(null);
  const [errorState, setErrorState] = useState<string | null>(null);

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setErrorState('Missing invitation token. Please check your invitation email link.');
      setIsLoading(false);
      return;
    }

    async function verifyToken() {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/verify-invite?token=${encodeURIComponent(token!)}`);
        const data = await res.json();
        if (!res.ok || !data.valid) {
          setErrorState(data.detail || 'This staff invitation link is invalid or has expired.');
        } else {
          setInviteData(data);
        }
      } catch (err: any) {
        setErrorState('Unable to verify invitation link. Please check your network connection.');
      } finally {
        setIsLoading(false);
      }
    }

    verifyToken();
  }, [token]);

  const handleAcceptInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (password.length < 8) {
      setSubmitError('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setSubmitError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/accept-invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invite_token: token,
          password: password,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to accept staff invitation.');
      }

      // Perform standard session cookie login
      await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteData?.email, password }),
      });

      await refreshSession();

      if (data.user?.role === 'system_admin') {
        router.push('/admin/system');
      } else if (data.user?.role === 'event_admin') {
        router.push('/admin/event');
      } else {
        router.push('/overview');
      }
    } catch (err: any) {
      setSubmitError(err.message || 'Error completing account setup.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl p-8 z-10 relative">
        <div className="flex flex-col items-center mb-6 text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 mb-3">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl font-black text-white tracking-wider">
            CROWD<span className="text-cyan-400">SHIELD</span> STAFF PROVISIONING
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-semibold uppercase tracking-wider">
            Complete Account Activation
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
            <p className="text-xs text-slate-400 font-mono">Verifying invitation credentials...</p>
          </div>
        )}

        {/* Honest Error State for Invalid / Expired Token */}
        {!isLoading && errorState && (
          <div className="space-y-6">
            <div className="bg-rose-950/80 border border-rose-500/40 text-rose-200 p-5 rounded-2xl flex items-start gap-4">
              <XCircle className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-bold text-sm text-rose-200">Invitation Link Invalid or Expired</h3>
                <p className="text-xs text-rose-300 mt-1.5 leading-relaxed">{errorState}</p>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <Link
                href="/auth/login"
                className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-2.5 text-center rounded-xl text-xs transition"
              >
                Return to Login Page
              </Link>
            </div>
          </div>
        )}

        {/* Valid Invite Form */}
        {!isLoading && inviteData && (
          <div className="space-y-6">
            {/* Staff Credentials Preview Badge */}
            <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <UserCheck className="w-4 h-4 text-cyan-400" />
                <span>Assigned Staff Identity</span>
              </div>

              <div className="pt-1 flex justify-between items-center">
                <div>
                  <div className="text-sm font-bold text-white">{inviteData.name}</div>
                  <div className="text-xs text-slate-400 font-mono">{inviteData.email}</div>
                </div>
                <div className="px-3 py-1 bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-[10px] font-extrabold uppercase rounded-lg tracking-wider">
                  {inviteData.role.replace('_', ' ')}
                </div>
              </div>
            </div>

            {submitError && (
              <div className="bg-rose-950/80 border border-rose-500/40 text-rose-300 p-3 rounded-xl text-xs font-semibold">
                {submitError}
              </div>
            )}

            <form onSubmit={handleAcceptInvite} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                  Create Account Password
                </label>
                <div className="relative">
                  <Lock className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-3 px-4 rounded-xl text-sm transition shadow-lg shadow-cyan-600/25 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <span>Activating Account...</span>
                ) : (
                  <>
                    <span>Activate Account & Enter Platform</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">Loading...</div>}>
      <AcceptInviteContent />
    </React.Suspense>
  );
}

