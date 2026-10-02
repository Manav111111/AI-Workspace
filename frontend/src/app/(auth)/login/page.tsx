'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import Logo from '@/components/brand/Logo';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.login({ email, password });
      // Fetch user companies to establish active company
      const profile = await api.getMe();
      if (profile.companies.length > 0) {
        localStorage.setItem('active_company_id', profile.companies[0].company.id);
      }
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setEmail('demo@avtaar.ai');
    setPassword('Demo12345!');
    setLoading(true);
    setError(null);
    try {
      await api.demoLogin();
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Demo login failed. Please retry in a moment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex flex-col justify-center items-center px-4 font-sans selection:bg-orange-950 selection:text-orange-300">
      <div className="max-w-sm w-full">
        {/* Brand Header */}
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="mb-4">
            <Logo variant="full" href="/" />
          </div>
          <h2 className="text-xl font-display font-bold text-[#F5F5F5] tracking-tight">Sign in to your account</h2>
          <p className="mt-1 text-xs text-[#737373]">
            Access your enterprise workspace and manage AI employees
          </p>
        </div>

        {/* Demo Account Quick Access Card */}
        <div className="mb-4 p-4 rounded-xl bg-orange-950/30 border border-[#FF9D00]/40 shadow-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#FFC247] flex items-center gap-1.5 font-display">
              <span>⚡ Pre-Configured Demo Workspace</span>
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-orange-900/60 text-orange-200 font-mono">
              Ready to Test
            </span>
          </div>
          <p className="text-[11px] text-[#A1A1AA] mb-3 leading-relaxed">
            Includes 2 Active AI Employees (Maya &amp; Alex), indexed customer &amp; HR knowledge bases, and live agent tools.
          </p>
          <button
            type="button"
            disabled={loading}
            onClick={handleDemoLogin}
            className="w-full py-2 px-3 bg-[#FF9D00] hover:bg-[#FF6A00] border border-[#FF9D00]/70 text-black text-xs font-semibold rounded-lg shadow-orange-sm transition-editorial flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Entering Demo Workspace...</span>
              </>
            ) : (
              <>
                <span>1-Click Instant Demo Login</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>

        {/* Card */}
        <div className="bg-[#101010] border border-[#262626] rounded-xl p-6 sm:p-7 shadow-card">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-950/60 border border-rose-800/50 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                Work Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@company.com"
                className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00] transition-editorial"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00] transition-editorial"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-[#151515] hover:bg-[#202020] border border-[#262626] hover:border-[#383838] disabled:opacity-50 text-[#F5F5F5] text-xs font-semibold rounded-lg transition-editorial flex items-center justify-center gap-2 mt-6"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In with Custom Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-[#737373]">
          Don&apos;t have an account yet?{' '}
          <Link href="/signup" className="text-[#FF9D00] hover:text-[#FF6A00] font-medium transition-editorial">
            Create workspace
          </Link>
        </p>
      </div>
    </div>
  );
}

