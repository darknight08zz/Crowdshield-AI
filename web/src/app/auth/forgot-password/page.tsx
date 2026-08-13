'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Shield, Mail, ArrowLeft, CheckCircle2, AlertTriangle } from 'lucide-react';
import { API_BASE_URL } from '@/lib/constants';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [devResetToken, setDevResetToken] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/request-reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to request reset link.');

      setSubmitted(true);
      if (data.dev_reset_token) {
        setDevResetToken(data.dev_reset_token);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred.');
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
          <h1 className="text-xl font-black text-white tracking-wider">RESET PASSWORD</h1>
          <p className="text-xs text-slate-400 mt-1">Enter your registered official email to receive instructions</p>
        </div>

        {submitted ? (
          <div className="space-y-6 text-center">
            <div className="bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 p-5 rounded-2xl flex flex-col items-center gap-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              <div className="font-bold text-sm text-emerald-200">Reset Instructions Dispatched</div>
              <p className="text-xs text-slate-300 mt-1">
                If an account exists for <strong className="text-white">{email}</strong>, password reset instructions have been sent.
              </p>
            </div>

            {devResetToken && (
              <div className="bg-slate-950 border border-slate-800 p-3 rounded-xl text-left text-xs font-mono">
                <div className="text-cyan-400 font-bold mb-1">Development Mode Link:</div>
                <Link
                  href={`/auth/reset-password?token=${devResetToken}`}
                  className="text-cyan-300 underline break-all"
                >
                  /auth/reset-password?token={devResetToken}
                </Link>
              </div>
            )}

            <Link
              href="/auth/login"
              className="inline-flex items-center gap-2 text-xs font-bold text-cyan-400 hover:text-cyan-300 transition"
            >
              <ArrowLeft className="w-4 h-4" />
              Return to Login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-rose-950/80 border border-rose-500/40 text-rose-300 p-3 rounded-xl text-xs font-semibold">
                {error}
              </div>
            )}

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
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-3 px-4 rounded-xl text-sm transition shadow-lg shadow-cyan-600/25 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? 'Sending Request...' : 'Send Reset Link'}
            </button>

            <div className="text-center">
              <Link
                href="/auth/login"
                className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white transition font-semibold"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
