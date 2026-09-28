import Link from 'next/link';
import {
  Bot,
  ShieldCheck,
  Database,
  ArrowRight,
  Activity,
  Coins,
  FlaskConical,
  BarChart3,
  Wrench,
  BookOpen,
  Terminal,
  Lock,
  Zap,
} from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Logo from '@/components/brand/Logo';

export default function Home() {
  return (
    <main className="min-h-screen bg-[#050505] text-[#F5F5F5] flex flex-col font-sans selection:bg-orange-950 selection:text-orange-300">
      {/* Top Navigation */}
      <header className="border-b border-[#262626] bg-[#050505]/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Logo variant="full" href="/" />
        </div>

        <nav className="hidden md:flex items-center gap-6 text-xs text-[#A1A1AA]">
          <Link href="#features" className="hover:text-[#F5F5F5] transition-editorial">Capabilities</Link>
          <Link href="/playground" className="hover:text-[#F5F5F5] transition-editorial">Playground</Link>
          <Link href="/evaluations" className="hover:text-[#F5F5F5] transition-editorial">Evaluations</Link>
          <Link href="/observability" className="hover:text-[#F5F5F5] transition-editorial">Observability</Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="px-3.5 py-1.5 text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] transition-editorial"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="px-4 py-1.5 text-xs font-semibold text-black bg-[#FF9D00] hover:bg-[#FF6A00] border border-[#FF9D00]/60 rounded-lg shadow-orange-sm transition-editorial flex items-center gap-1.5"
          >
            Launch Workspace
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="flex-1 max-w-5xl mx-auto px-6 pt-20 pb-16 flex flex-col items-center text-center justify-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#101010] border border-[#262626] text-[#FFC247] text-xs font-mono mb-8 shadow-card">
          <span className="w-2 h-2 rounded-full bg-[#FF9D00]" />
          <span>Enterprise Multi-Tenant AI Infrastructure</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-display font-bold tracking-tight max-w-4xl leading-[1.12] text-[#F5F5F5]">
          The Enterprise Control Plane for{' '}
          <span className="text-[#FF9D00]">
            AI Employees
          </span>
        </h1>

        <p className="mt-6 text-base sm:text-lg text-[#A1A1AA] max-w-2xl leading-relaxed font-sans">
          Create, deploy, evaluate, and govern AI employees with production-ready retrieval,
          agent workflows, observability, and cost controls.
        </p>

        <div className="mt-8 flex flex-wrap gap-3 justify-center">
          <Link
            href="/signup"
            className="px-6 py-3 text-xs sm:text-sm font-semibold text-black bg-[#FF9D00] hover:bg-[#FF6A00] border border-[#FF9D00]/60 rounded-lg shadow-orange-sm transition-editorial flex items-center gap-2"
          >
            Create Company Workspace
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 text-xs sm:text-sm font-medium text-[#F5F5F5] hover:text-white bg-[#101010] hover:bg-[#151515] border border-[#262626] hover:border-[#383838] rounded-lg transition-editorial shadow-card"
          >
            Explore Platform
          </Link>
        </div>

        {/* Live Architecture Capabilities Banner */}
        <div className="mt-14 w-full p-4 rounded-xl bg-[#0B0B0B] border border-[#262626] grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
          <div className="border-r border-[#262626]/60 pr-2 last:border-r-0">
            <div className="text-[11px] font-mono text-[#737373] uppercase">Retrieval Engine</div>
            <div className="text-sm font-semibold text-[#F5F5F5] mt-0.5">Hybrid Dense + BM25</div>
          </div>
          <div className="border-r border-[#262626]/60 pr-2 last:border-r-0">
            <div className="text-[11px] font-mono text-[#737373] uppercase">Evaluation Metric</div>
            <div className="text-sm font-semibold text-[#F5F5F5] mt-0.5">Recall@K &amp; MRR Gates</div>
          </div>
          <div className="border-r border-[#262626]/60 pr-2 last:border-r-0">
            <div className="text-[11px] font-mono text-[#737373] uppercase">Telemetry</div>
            <div className="text-sm font-semibold text-[#F5F5F5] mt-0.5">OTel Spans &amp; PII Redaction</div>
          </div>
          <div>
            <div className="text-[11px] font-mono text-[#737373] uppercase">Security Standard</div>
            <div className="text-sm font-semibold text-[#F5F5F5] mt-0.5">Strict Tenant Boundaries</div>
          </div>
        </div>

        {/* Feature Grid */}
        <div id="features" className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-4 text-left w-full">
          <div className="p-6 rounded-xl bg-[#101010] border border-[#262626] hover:border-[#383838] transition-editorial shadow-card">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4">
              <Database className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-display font-semibold text-[#F5F5F5]">Hybrid RAG &amp; Retrieval</h3>
            <p className="mt-2 text-xs text-[#A1A1AA] leading-relaxed">
              Dense vector embeddings coupled with BM25 sparse keyword index, reciprocal rank fusion (RRF), and cross-encoder reranking.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#101010] border border-[#262626] hover:border-[#383838] transition-editorial shadow-card">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4">
              <FlaskConical className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-display font-semibold text-[#F5F5F5]">AI Playground &amp; Evaluation</h3>
            <p className="mt-2 text-xs text-[#A1A1AA] leading-relaxed">
              Debug prompt assembly, inspect retrieved citation chunks, and benchmark accuracy against Golden Datasets with automated regression gates.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#101010] border border-[#262626] hover:border-[#383838] transition-editorial shadow-card">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4">
              <Activity className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-display font-semibold text-[#F5F5F5]">Observability &amp; Tracing</h3>
            <p className="mt-2 text-xs text-[#A1A1AA] leading-relaxed">
              OpenTelemetry-native distributed spans across vector search, LLM calls, and tool execution with automatic PII sanitization.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#101010] border border-[#262626] hover:border-[#383838] transition-editorial shadow-card">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4">
              <Coins className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-display font-semibold text-[#F5F5F5]">Cost Governance &amp; Budgets</h3>
            <p className="mt-2 text-xs text-[#A1A1AA] leading-relaxed">
              Precise token usage metering, model price registry mapping, tenant cost ledgers, soft warning alerts, and hard budget enforcement.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#101010] border border-[#262626] hover:border-[#383838] transition-editorial shadow-card">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4">
              <Wrench className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-display font-semibold text-[#F5F5F5]">Agent Tools &amp; Approvals</h3>
            <p className="mt-2 text-xs text-[#A1A1AA] leading-relaxed">
              Autonomous tool calling with strict schema validation and interactive human-in-the-loop approval gates for sensitive operations.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#101010] border border-[#262626] hover:border-[#383838] transition-editorial shadow-card">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mb-4">
              <BookOpen className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-display font-semibold text-[#F5F5F5]">Knowledge Base Management</h3>
            <p className="mt-2 text-xs text-[#A1A1AA] leading-relaxed">
              Multi-format document ingestion, semantic chunking, and real-time chunk inspection with strict company-level tenant isolation.
            </p>
          </div>
        </div>

        {/* Technical Status Strip */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-2 text-xs text-[#737373]">
          <Badge variant="orange" dot>Distributed Rate Limiter</Badge>
          <Badge variant="orange" dot>OpenTelemetry Traces</Badge>
          <Badge variant="forest" dot>Zero-Trust Tenant Boundaries</Badge>
          <Badge variant="neutral" dot>Embeddable Client SDK</Badge>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#262626] py-6 px-6 text-center text-xs text-[#737373] bg-[#050505]">
        Avtaar Enterprise AI Employee Platform &bull; Production Infrastructure &bull; FastAPI &bull; Next.js &bull; Qdrant &bull; Redis
      </footer>
    </main>
  );
}

