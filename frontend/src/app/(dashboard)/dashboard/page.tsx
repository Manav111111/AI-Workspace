'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AIEmployee, KnowledgeBase, OperationalMetrics, UsageSummary } from '@/types';
import {
  Bot,
  Plus,
  BookOpen,
  MessageSquare,
  ArrowUpRight,
  Activity,
  FlaskConical,
  BarChart3,
  Coins,
  ArrowRight,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';

export default function DashboardPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [metrics, setMetrics] = useState<OperationalMetrics | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [empData, kbData, metricsData, usageData] = await Promise.all([
          api.getAIEmployees(),
          api.getKnowledgeBases(),
          api.getMetricsSummary().catch(() => null),
          api.getUsageSummary(undefined, 30).catch(() => null),
        ]);
        setEmployees(empData);
        setKnowledgeBases(kbData);
        if (metricsData) setMetrics(metricsData);
        if (usageData) setUsage(usageData);
      } catch (err) {
        // Handled in UI
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const activeEmployeesCount = employees.filter((e) => e.status === 'ACTIVE').length;

  return (
    <div className="max-w-7xl mx-auto space-y-7 font-sans">
      {/* Page Header */}
      <PageHeader
        title="Workspace Overview"
        description="Operational overview of enterprise AI employees, knowledge bases, traces, and cost governance."
        actions={
          <div className="flex items-center gap-2">
            <Link href="/playground">
              <Button variant="secondary" size="sm" icon={FlaskConical}>
                Open Playground
              </Button>
            </Link>
            <Link href="/ai-employees">
              <Button variant="primary" size="sm" icon={Plus}>
                Manage AI Employees
              </Button>
            </Link>
          </div>
        }
      />

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#737373] uppercase tracking-wider font-mono">AI Employees</span>
              <div className="w-8 h-8 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                <Bot className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl font-bold text-[#F5F5F5] font-mono">
              {loading ? '...' : employees.length}
            </div>
            <div className="mt-2 flex items-center gap-1.5 text-xs text-[#737373]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-[11px] text-[#A1A1AA]">{activeEmployeesCount} Active in runtime</span>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#737373] uppercase tracking-wider font-mono">Knowledge Bases</span>
              <div className="w-8 h-8 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                <BookOpen className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl font-bold text-[#F5F5F5] font-mono">
              {loading ? '...' : knowledgeBases.length}
            </div>
            <div className="mt-2 text-xs text-[#737373]">
              <span className="text-[11px]">Hybrid RAG with BM25 &amp; Qdrant</span>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#737373] uppercase tracking-wider font-mono">Metered Ops</span>
              <div className="w-8 h-8 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                <Activity className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl font-bold text-[#F5F5F5] font-mono">
              {loading ? '...' : metrics ? (metrics.requests_total || 0).toLocaleString() : '0'}
            </div>
            <div className="mt-2 text-xs text-[#737373]">
              <span className="text-[11px]">
                {metrics ? `${metrics.requests_success || 0} Successful ops` : 'Distributed Tracing active'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#737373] uppercase tracking-wider font-mono">30-Day Cost</span>
              <div className="w-8 h-8 rounded-lg bg-orange-950/60 border border-orange-800/50 flex items-center justify-center text-[#FFC247]">
                <Coins className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl font-bold text-[#F5F5F5] font-mono">
              {loading ? '...' : usage ? `$${(usage.total_estimated_cost || 0).toFixed(4)}` : '$0.0000'}
            </div>
            <div className="mt-2 text-xs text-[#737373]">
              <span className="text-[11px]">
                {usage ? `${(usage.total_tokens || 0).toLocaleString()} Total Tokens` : 'Model price registry linked'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Launch & Workflows Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/playground" className="group">
          <Card hover className="h-full border-[#262626] group-hover:border-[#383838]">
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                  <FlaskConical className="w-4 h-4" />
                </div>
                <Badge variant="orange">Debug</Badge>
              </div>
              <div>
                <h3 className="text-sm font-display font-semibold text-[#F5F5F5] group-hover:text-[#FF9D00] transition-editorial">
                  AI Employee Playground
                </h3>
                <p className="text-xs text-[#737373] mt-1 leading-relaxed font-sans">
                  Test prompt assembly, vector citations, and live tool invocations with isolated debug sessions.
                </p>
              </div>
              <div className="text-xs text-[#FF9D00] font-medium flex items-center gap-1 pt-2">
                <span>Launch playground</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-editorial" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/evaluations" className="group">
          <Card hover className="h-full border-[#262626] group-hover:border-[#383838]">
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                  <BarChart3 className="w-4 h-4" />
                </div>
                <Badge variant="orange">Benchmark</Badge>
              </div>
              <div>
                <h3 className="text-sm font-display font-semibold text-[#F5F5F5] group-hover:text-[#FF9D00] transition-editorial">
                  RAG Benchmark Evaluations
                </h3>
                <p className="text-xs text-[#737373] mt-1 leading-relaxed font-sans">
                  Run golden test datasets against hybrid retrieval to verify Recall@K, MRR, and NDCG accuracy.
                </p>
              </div>
              <div className="text-xs text-[#FF9D00] font-medium flex items-center gap-1 pt-2">
                <span>View benchmarks</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-editorial" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/observability" className="group">
          <Card hover className="h-full border-[#262626] group-hover:border-[#383838]">
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                  <Activity className="w-4 h-4" />
                </div>
                <Badge variant="neutral">OpenTelemetry</Badge>
              </div>
              <div>
                <h3 className="text-sm font-display font-semibold text-[#F5F5F5] group-hover:text-[#FF9D00] transition-editorial">
                  Distributed Traces &amp; Telemetry
                </h3>
                <p className="text-xs text-[#737373] mt-1 leading-relaxed font-sans">
                  Trace request latencies across retrieval, LLM calls, and tools with automatic PII redaction.
                </p>
              </div>
              <div className="text-xs text-[#A1A1AA] font-medium flex items-center gap-1 pt-2">
                <span>Inspect traces</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-editorial" />
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* AI Employees Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div>
              <h2 className="text-sm font-display font-semibold text-[#F5F5F5] tracking-tight">Active AI Employees</h2>
              <p className="text-xs text-[#737373] mt-0.5">Configured employees in this workspace</p>
            </div>
            <Link
              href="/ai-employees"
              className="text-xs font-semibold text-[#FF9D00] hover:text-[#FF6A00] flex items-center gap-1 transition-editorial"
            >
              <span>View all employees</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </CardHeader>

        <CardContent className="p-5">
          {loading ? (
            <div className="py-8 text-center text-xs text-[#737373] font-mono">Loading AI employees...</div>
          ) : employees.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="No AI Employees created"
              description="Create your first AI employee to configure its role, personality, assigned knowledge bases, and tools."
              actionText="Create AI Employee"
              actionIcon={Plus}
              onAction={() => (window.location.href = '/ai-employees')}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {employees.map((emp) => (
                <div
                  key={emp.id}
                  className="p-4 rounded-xl bg-[#151515] border border-[#262626] hover:border-[#383838] transition-editorial flex flex-col justify-between space-y-3 shadow-card"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-display font-semibold text-[#F5F5F5]">{emp.name}</h3>
                      <p className="text-xs text-[#FF9D00] font-mono mt-0.5">{emp.role}</p>
                    </div>
                    <Badge variant={emp.status === 'ACTIVE' ? 'forest' : 'orange'} dot>
                      {emp.status}
                    </Badge>
                  </div>
                  {emp.description && (
                    <p className="text-xs text-[#737373] line-clamp-2 leading-relaxed font-sans">
                      {emp.description}
                    </p>
                  )}
                  <div className="pt-2 border-t border-[#262626] flex items-center justify-between text-xs">
                    <Link
                      href={`/ai-employees/${emp.id}/chat`}
                      className="text-[#FF9D00] hover:text-[#FF6A00] font-medium flex items-center gap-1"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>Chat</span>
                    </Link>
                    <Link
                      href="/ai-employees"
                      className="text-[#737373] hover:text-[#F5F5F5]"
                    >
                      Configure &rarr;
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

