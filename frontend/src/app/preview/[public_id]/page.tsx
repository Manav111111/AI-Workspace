'use client';

import React, { useEffect, useState } from 'react';
import Script from 'next/script';
import Link from 'next/link';
import { Bot, Sparkles, ArrowLeft, ShieldCheck, Layers, ExternalLink } from 'lucide-react';
import { api } from '@/lib/api';
import { PublicEmployeeConfig } from '@/types';

export default function StandaloneWidgetPreviewPage({
  params,
}: {
  params: { public_id: string };
}) {
  const publicId = params.public_id;
  const [config, setConfig] = useState<PublicEmployeeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!publicId) return;

    api
      .getPublicEmployeeConfig(publicId)
      .then((cfg) => {
        setConfig(cfg);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'AI Employee not found or is unpublished.');
        setLoading(false);
      });
  }, [publicId]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Demo Nav */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/ai-employees"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors flex items-center gap-1 text-xs"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Dashboard</span>
          </Link>
          <div className="h-4 w-px bg-slate-800" />
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-400 font-mono">External Host Website Simulation</span>
          </div>
        </div>

        {config && (
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <span>Widget Target:</span>
            <strong className="text-indigo-400 font-medium">{config.name}</strong>
            <span className="text-slate-600">•</span>
            <span className="font-mono text-[11px] text-slate-500">{publicId}</span>
          </div>
        )}
      </header>

      {/* Main Simulated Host Site Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-6 sm:p-12 flex flex-col items-center justify-center text-center space-y-6">
        {loading ? (
          <div className="space-y-4 animate-pulse max-w-md w-full">
            <div className="h-8 bg-slate-800 rounded w-3/4 mx-auto" />
            <div className="h-4 bg-slate-800 rounded w-full" />
            <div className="h-4 bg-slate-800 rounded w-5/6 mx-auto" />
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 max-w-lg space-y-3">
            <h3 className="text-base font-semibold">Widget Unavailable</h3>
            <p className="text-xs text-slate-300">{error}</p>
            <div className="pt-2">
              <Link
                href="/ai-employees"
                className="inline-flex px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium"
              >
                Return to AI Employees
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Avtaar Standalone Embed Widget Demo</span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white max-w-2xl">
              Welcome to Acme Corp Customer Portal
            </h1>

            <p className="text-sm sm:text-base text-slate-400 max-w-xl leading-relaxed">
              This sandbox webpage demonstrates the real-world deployment of your AI Employee{' '}
              <strong className="text-indigo-400 font-semibold">{config?.name}</strong> using the
              standalone <code className="text-slate-200 bg-slate-800 px-1.5 py-0.5 rounded text-xs">widget.js</code> tag.
            </p>

            {/* Simulated website features */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full pt-8 text-left">
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h4 className="text-xs font-semibold text-slate-200">Shadow DOM Isolation</h4>
                <p className="text-[11px] text-slate-400">
                  Styles from this host page do not interfere with the floating widget.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                <h4 className="text-xs font-semibold text-slate-200">Grounded RAG</h4>
                <p className="text-[11px] text-slate-400">
                  Click the launcher in the corner to test retrieval and tool executions in real time.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
                <Bot className="w-5 h-5 text-purple-400" />
                <h4 className="text-xs font-semibold text-slate-200">Session Resumption</h4>
                <p className="text-[11px] text-slate-400">
                  Refreshing the page restores previous message history via anonymous visitor session.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 max-w-md text-xs text-slate-400 mt-4">
              👉 Look at the <strong>bottom-right (or configured position)</strong> of the screen to click the floating launcher and start a chat session.
            </div>
          </>
        )}
      </main>

      {/* Load the actual standalone widget.js script using public_id */}
      {config && (
        <Script
          src="/widget.js"
          strategy="afterInteractive"
          data-ai-employee={publicId}
          data-api-base={process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
        />
      )}
    </div>
  );
}
