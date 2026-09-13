import Link from 'next/link';
import { Bot, ShieldCheck, Database, Cpu, Sparkles, ArrowRight, Layers, Lock } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0b0f19] text-white flex flex-col">
      {/* Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="font-bold text-lg tracking-tight">AI Employee Platform</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="flex-1 max-w-5xl mx-auto px-6 py-20 flex flex-col items-center text-center justify-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono mb-6">
          <ShieldCheck className="w-4 h-4" />
          <span>Phase 0: Enterprise Architecture & Multi-Tenancy Foundation</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight max-w-3xl leading-tight">
          Enterprise Multi-Tenant{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
            AI Employee
          </span>{' '}
          Infrastructure
        </h1>

        <p className="mt-6 text-lg text-slate-400 max-w-2xl leading-relaxed">
          A scalable, production-grade foundation built with strict tenant isolation, layered services,
          and extensible domain entities engineered for future RAG, autonomous agents, and realistic 3D avatar interfaces.
        </p>

        <div className="mt-8 flex flex-wrap gap-4 justify-center">
          <Link
            href="/signup"
            className="px-6 py-3 text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2"
          >
            Create Company Workspace
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 text-base font-semibold text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition-all"
          >
            Open Dashboard
          </Link>
        </div>

        {/* Feature Grid */}
        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 text-left w-full">
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4 border border-indigo-500/20">
              <Lock className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Strict Multi-Tenancy</h3>
            <p className="mt-2 text-sm text-slate-400">
              Zero cross-tenant leakage. Every query, entity, and repository boundary is strictly filtered by authorized company memberships.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/40 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4 border border-purple-500/20">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Modular Monolith</h3>
            <p className="mt-2 text-sm text-slate-400">
              Clean separation across API, Service, Repository, and Database layers without premature microservices complexity.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-pink-500/40 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-pink-500/10 flex items-center justify-center text-pink-400 mb-4 border border-pink-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Decoupled Architecture</h3>
            <p className="mt-2 text-sm text-slate-400">
              Prepares extensible hooks for future Qdrant vector retrieval, STT/TTS voice, and 3D avatar rendering without local GPU coupling.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 px-6 text-center text-xs text-slate-400">
        AI Employee Platform &bull; Phase 0 Production Foundation &bull; Python FastAPI &bull; Next.js &bull; PostgreSQL
      </footer>
    </main>
  );
}
