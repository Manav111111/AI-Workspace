'use client';

import React, { useEffect, useState } from 'react';
import Script from 'next/script';
import Link from 'next/link';
import { Bot, Sparkles, ArrowLeft, ShieldCheck, Layers } from 'lucide-react';
import { api } from '@/lib/api';
import { PublicEmployeeConfig } from '@/types';
import { Card, CardContent } from '@/components/ui/Card';

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
    <div className="min-h-screen bg-[#050505] text-[#F5F5F5] flex flex-col font-sans selection:bg-[#FF9D00]/20 selection:text-[#FF9D00]">
      {/* Top Demo Nav */}
      <header className="border-b border-[#262626] bg-[#0B0B0B]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/ai-employees"
            className="p-1.5 rounded-lg bg-[#151515] hover:bg-[#1E1E1E] text-[#A1A1AA] hover:text-[#F5F5F5] transition-colors flex items-center gap-1.5 text-xs font-semibold"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Dashboard</span>
          </Link>
          <div className="h-4 w-px bg-[#262626]" />
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-[#FF9D00] animate-pulse" />
            <span className="text-[#737373] font-mono">External Host Website Sandbox</span>
          </div>
        </div>

        {config && (
          <div className="text-xs text-[#737373] flex items-center gap-2">
            <span>Widget Target:</span>
            <strong className="text-[#FF9D00] font-semibold">{config.name}</strong>
            <span className="text-[#262626]">•</span>
            <span className="font-mono text-[11px] text-[#A1A1AA]">{publicId}</span>
          </div>
        )}
      </header>

      {/* Main Simulated Host Site Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-6 sm:p-12 flex flex-col items-center justify-center text-center space-y-6">
        {loading ? (
          <div className="space-y-4 animate-pulse max-w-md w-full">
            <div className="h-8 bg-[#151515] rounded w-3/4 mx-auto" />
            <div className="h-4 bg-[#151515] rounded w-full" />
            <div className="h-4 bg-[#151515] rounded w-5/6 mx-auto" />
          </div>
        ) : error ? (
          <div className="p-6 rounded-xl bg-rose-950/40 border border-rose-900/60 text-rose-300 max-w-lg space-y-3">
            <h3 className="text-base font-semibold font-display">Widget Unavailable</h3>
            <p className="text-xs text-[#A1A1AA]">{error}</p>
            <div className="pt-2">
              <Link
                href="/ai-employees"
                className="inline-flex px-4 py-2 bg-[#151515] hover:bg-[#1E1E1E] border border-[#262626] text-[#F5F5F5] rounded-lg text-xs font-semibold transition-colors"
              >
                Return to AI Employees
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#151515] border border-[#262626] text-[#FF9D00] text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5 text-[#FF9D00]" />
              <span>Avtaar Standalone Embed Widget Sandbox</span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-bold font-display tracking-tight text-[#F5F5F5] max-w-2xl leading-tight">
              Customer Portal Simulation
            </h1>

            <p className="text-sm sm:text-base text-[#A1A1AA] max-w-xl leading-relaxed">
              This sandbox webpage demonstrates the real-world deployment of your AI Employee{' '}
              <strong className="text-[#FF9D00] font-semibold">{config?.name}</strong> using the
              standalone <code className="text-[#F5F5F5] bg-[#151515] border border-[#262626] px-1.5 py-0.5 rounded text-xs font-mono">widget.js</code> script.
            </p>

            {/* Simulated website features */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full pt-8 text-left">
              <Card>
                <CardContent className="p-4 space-y-2">
                  <ShieldCheck className="w-5 h-5 text-[#FF9D00]" />
                  <h4 className="text-xs font-semibold font-display text-[#F5F5F5]">Shadow DOM Isolation</h4>
                  <p className="text-[11px] text-[#A1A1AA] leading-relaxed">
                    Styles from this host page do not bleed into or interfere with the floating widget.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4 space-y-2">
                  <Layers className="w-5 h-5 text-[#FFC247]" />
                  <h4 className="text-xs font-semibold font-display text-[#F5F5F5]">Grounded RAG</h4>
                  <p className="text-[11px] text-[#A1A1AA] leading-relaxed">
                    Click the launcher in the corner to test retrieval citations and tool executions in real time.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-4 space-y-2">
                  <Bot className="w-5 h-5 text-[#FF9D00]" />
                  <h4 className="text-xs font-semibold font-display text-[#F5F5F5]">Session Resumption</h4>
                  <p className="text-[11px] text-[#A1A1AA] leading-relaxed">
                    Refreshing the page restores previous message history via anonymous visitor session.
                  </p>
                </CardContent>
              </Card>
            </div>

            <div className="p-4 rounded-xl bg-[#101010] border border-[#262626] max-w-md text-xs text-[#A1A1AA] mt-4">
              Look at the <strong className="text-[#FF9D00]">bottom-right</strong> of the screen to click the floating launcher and start a chat session.
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
