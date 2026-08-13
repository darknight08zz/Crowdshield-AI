'use client';

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Shield, Lock, Mail, AlertTriangle, ArrowRight } from 'lucide-react';

import { useAuth } from '@/components/providers/AuthProvider';

function LoginContent() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectPath = searchParams.get('redirect');
  const { refreshSession } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Login authentication failed');
      }

      await refreshSession();

      if (redirectPath) {
        router.push(redirectPath);
      } else {
        const userRole = data.user?.role;
        if (userRole === 'system_admin') {
          router.push('/admin/system');
        } else if (userRole === 'event_admin') {
          router.push('/admin/event');
        } else {
          router.push('/overview');
        }
      }
      router.refresh();
    } catch (err: any) {
      setError(err.message || 'Unable to sign in. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md card-command p-8 z-10 relative shadow-2xl">
        {/* Brand Header */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-xl shadow-cyan-500/25 mb-4 border border-cyan-400/30">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-wider">
            CROWD<span className="text-cyan-400">SHIELD</span>
          </h1>
          <p className="text-xs font-semibold text-slate-400 mt-1 uppercase tracking-widest">
            Public Safety Command & Operations Platform
          </p>
        </div>

        {/* Error Alert Banner */}
        {error && (
          <div className="mb-6 bg-rose-950/80 border border-rose-500/40 text-rose-300 p-4 rounded-xl flex items-start gap-3 text-sm animate-fadeIn">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-rose-200">Authentication Failed</div>
              <div className="text-xs mt-0.5 text-rose-300">{error}</div>
            </div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
              Official Email Address
            </label>
            <div className="relative">
              <Mail className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@crowdshield.gov"
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                Password
              </label>
              <Link
                href="/auth/forgot-password"
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Lock className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <span>Authenticating Session...</span>
            ) : (
              <>
                <span>Sign In to Command Portal</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">Loading...</div>}>
      <LoginContent />
    </React.Suspense>
  );
}


