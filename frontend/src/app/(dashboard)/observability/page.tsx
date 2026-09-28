'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import {
  AIEmployee,
  OperationalMetrics,
  Span,
  TraceSummary,
} from '@/types';
import {
  Activity,
  CheckCircle2,
  Clock,
  Cpu,
  Network,
  RefreshCw,
  Search,
  X,
  Zap,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export default function ObservabilityPage() {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [metrics, setMetrics] = useState<OperationalMetrics | null>(null);
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Trace & Drawer
  const [selectedTrace, setSelectedTrace] = useState<TraceSummary | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [fetchedTraces, fetchedMetrics, fetchedEmployees] = await Promise.all([
        api.listTraces({ limit: 50 }),
        api.getMetricsSummary(),
        api.getAIEmployees(),
      ]);
      setTraces(fetchedTraces);
      setMetrics(fetchedMetrics);
      setEmployees(fetchedEmployees);
    } catch (err) {
      console.error('Failed to load observability data:', err);
    } finally {
      setLoading(false);
    }
  }

  async function refreshData() {
    setRefreshing(true);
    try {
      const [fetchedTraces, fetchedMetrics] = await Promise.all([
        api.listTraces({
          ai_employee_id: selectedEmployeeId !== 'ALL' ? selectedEmployeeId : undefined,
          limit: 50,
        }),
        api.getMetricsSummary(),
      ]);
      setTraces(fetchedTraces);
      setMetrics(fetchedMetrics);
    } catch (err) {
      console.error('Failed to refresh observability data:', err);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleSelectTrace(trace: TraceSummary) {
    try {
      const fullTrace = await api.getTrace(trace.trace_id);
      setSelectedTrace(fullTrace);
      if (fullTrace.spans_data && fullTrace.spans_data.length > 0) {
        setSelectedSpan(fullTrace.spans_data[0]);
      } else {
        setSelectedSpan(null);
      }
    } catch (err) {
      console.error('Failed to fetch full trace:', err);
      setSelectedTrace(trace);
      setSelectedSpan(trace.spans_data?.[0] || null);
    }
  }

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      if (selectedEmployeeId !== 'ALL' && t.ai_employee_id !== selectedEmployeeId) {
        return false;
      }
      if (selectedStatus !== 'ALL' && t.status !== selectedStatus) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesTraceId = t.trace_id.toLowerCase().includes(query);
        const matchesReqType = t.request_type.toLowerCase().includes(query);
        const matchesError = t.error_message?.toLowerCase().includes(query);
        if (!matchesTraceId && !matchesReqType && !matchesError) return false;
      }
      return true;
    });
  }, [traces, selectedEmployeeId, selectedStatus, searchQuery]);

  const getSpanColor = (name: string) => {
    if (name.includes('llm') || name.includes('generate')) {
      return { text: 'text-[#FF9D00]', bar: 'bg-[#FF9D00]' };
    }
    if (name.includes('retrieval') || name.includes('qdrant') || name.includes('bm25')) {
      return { text: 'text-[#FFC247]', bar: 'bg-[#FFC247]' };
    }
    if (name.includes('tool') || name.includes('action')) {
      return { text: 'text-blue-400', bar: 'bg-blue-500' };
    }
    if (name.includes('prompt') || name.includes('assemble')) {
      return { text: 'text-[#A1A1AA]', bar: 'bg-[#737373]' };
    }
    return { text: 'text-[#FF9D00]', bar: 'bg-[#FF9D00]' };
  };

  const getEmployeeName = (id?: string | null) => {
    if (!id) return 'System / Shared';
    const found = employees.find((e) => e.id === id);
    return found ? found.name : `${id.slice(0, 8)}...`;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <PageHeader
        title="Distributed Tracing & Telemetry"
        description="OpenTelemetry native request trace trees, latency percentiles, breakdown spans, and production audit telemetry with automatic PII redaction."
        badge={<Badge variant="orange">W3C Trace Context</Badge>}
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            loading={refreshing}
            onClick={refreshData}
          >
            Refresh
          </Button>
        }
      />

      {/* Operational Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[#737373] font-mono">Total Throughput</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-[#FF9D00]">
                <Zap className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#F5F5F5] font-mono mb-1">
              {metrics?.requests_total ?? 0}
              <span className="text-xs text-[#737373] font-normal ml-1.5 font-sans">requests</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`font-medium flex items-center gap-1 ${
                  (metrics?.error_rate_percent ?? 0) === 0
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>
                  {100 - (metrics?.error_rate_percent ?? 0)}% Success Rate
                </span>
              </span>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[#737373] font-mono">P50 / P95 Latency</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-[#FF9D00]">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#F5F5F5] font-mono mb-1">
              {metrics?.latencies_ms?.total?.p50 ?? (metrics as any)?.latency_p50_ms ?? 0}
              <span className="text-xs text-[#737373] font-normal ml-1 font-sans">ms (p50)</span>
            </div>
            <div className="text-xs text-[#737373] font-mono">
              p95: <span className="text-[#FF9D00] font-semibold">{metrics?.latencies_ms?.total?.p95 ?? (metrics as any)?.latency_p95_ms ?? 0} ms</span>
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[#737373] font-mono">Captured Traces</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-[#A1A1AA]">
                <Network className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#F5F5F5] font-mono mb-1">
              {traces.length.toLocaleString()}
            </div>
            <div className="text-xs text-[#737373]">
              Distributed traces with OpenTelemetry spans
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[#737373] font-mono">Denials & Limits</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-amber-400">
                <Cpu className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#FFC247] font-mono mb-1">
              {((metrics?.budget_denials_total || 0) + (metrics?.rate_limit_denials_total || 0)).toLocaleString()}
            </div>
            <div className="text-xs text-[#737373]">
              Budgets: {metrics?.budget_denials_total || 0} &bull; Rate Limits: {metrics?.rate_limit_denials_total || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#737373]" />
              <input
                type="text"
                placeholder="Search by Trace ID, Request Type, or Error..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#0B0B0B] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
              />
            </div>

            <div className="flex items-center gap-3">
              <select
                value={selectedEmployeeId}
                onChange={(e) => setSelectedEmployeeId(e.target.value)}
                className="bg-[#0B0B0B] border border-[#262626] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
              >
                <option value="ALL">All AI Employees</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>

              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-[#0B0B0B] border border-[#262626] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
              >
                <option value="ALL">All Statuses</option>
                <option value="SUCCESS">Success Only</option>
                <option value="ERROR">Error Only</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Traces Table */}
      <Card>
        <CardHeader>
          <CardTitle subtitle="Chronological request trace logs with span breakdowns">
            <span>Trace Invocations ({filteredTraces.length})</span>
          </CardTitle>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#262626] bg-[#0B0B0B] text-[11px] font-mono text-[#737373] uppercase tracking-wider">
                  <th className="py-3 px-4">Request / Operation</th>
                  <th className="py-3 px-4">Trace ID</th>
                  <th className="py-3 px-4">AI Employee</th>
                  <th className="py-3 px-4">Spans</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262626] font-mono text-[11px]">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-[#737373] font-sans">
                      Loading traces...
                    </td>
                  </tr>
                ) : filteredTraces.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-[#737373] font-sans">
                      No traces matching active filters.
                    </td>
                  </tr>
                ) : (
                  filteredTraces.map((t) => {
                    const isSuccess = t.status === 'SUCCESS';
                    return (
                      <tr
                        key={t.trace_id}
                        onClick={() => handleSelectTrace(t)}
                        className="hover:bg-[#151515]/60 cursor-pointer transition-colors group"
                      >
                        <td className="py-3 px-4 font-sans font-medium text-[#F5F5F5] flex items-center gap-2">
                          <Activity className="w-3.5 h-3.5 text-[#FF9D00]" />
                          <span>{t.request_type}</span>
                        </td>
                        <td className="py-3 px-4 text-[#737373] font-mono">
                          {t.trace_id.slice(0, 16)}...
                        </td>
                        <td className="py-3 px-4 font-sans text-[#A1A1AA]">
                          {getEmployeeName(t.ai_employee_id)}
                        </td>
                        <td className="py-3 px-4 text-[#737373]">
                          {t.spans_count ?? t.spans_data?.length ?? 1} spans
                        </td>
                        <td className="py-3 px-4 font-bold text-[#F5F5F5]">
                          {t.total_latency_ms ? `${t.total_latency_ms.toFixed(0)} ms` : '< 1ms'}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={isSuccess ? 'forest' : 'rose'} dot>
                            {t.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right text-[#737373]">
                          {new Date(t.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Trace Waterfall Detail Drawer Modal */}
      {selectedTrace && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-4xl p-6 shadow-2xl max-h-[90vh] flex flex-col space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626] shrink-0">
              <div className="flex items-center gap-2.5">
                <Activity className="w-5 h-5 text-[#FF9D00]" />
                <div>
                  <h3 className="text-sm font-semibold font-display text-[#F5F5F5]">
                    Trace Waterfall: {selectedTrace.request_type}
                  </h3>
                  <p className="text-[11px] text-[#737373] font-mono">
                    ID: {selectedTrace.trace_id}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedTrace(null)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Waterfall Span Tree */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              <div className="text-[11px] font-mono text-[#737373] uppercase tracking-wider">
                Span Execution Breakdown
              </div>

              {selectedTrace.spans_data && selectedTrace.spans_data.length > 0 ? (
                selectedTrace.spans_data.map((span, idx) => {
                  const style = getSpanColor(span.name);
                  const durationPct = selectedTrace.total_latency_ms
                    ? Math.max(8, Math.min(100, (span.duration_ms / selectedTrace.total_latency_ms) * 100))
                    : 100;

                  return (
                    <div
                      key={span.span_id || idx}
                      onClick={() => setSelectedSpan(span)}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedSpan?.span_id === span.span_id
                          ? 'bg-[#151515] border-[#FF9D00]/40'
                          : 'bg-[#0B0B0B] border-[#262626] hover:bg-[#151515]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className={`font-mono font-bold ${style.text}`}>
                          {span.name}
                        </span>
                        <span className="font-mono text-[11px] text-[#A1A1AA]">
                          {span.duration_ms ? `${span.duration_ms.toFixed(1)} ms` : '< 1ms'}
                        </span>
                      </div>

                      {/* Progress Visual Bar */}
                      <div className="w-full bg-[#1A1A1A] h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${style.bar}`}
                          style={{ width: `${durationPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-xs text-[#737373] font-mono">
                  No child spans recorded for this trace.
                </div>
              )}

              {/* Selected Span Attributes Inspector */}
              {selectedSpan && (
                <div className="mt-4 p-4 bg-[#0B0B0B] rounded-lg border border-[#262626] space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-[#F5F5F5]">
                    <span>Span Attributes: {selectedSpan.name}</span>
                    <Badge variant="orange">PII Redacted</Badge>
                  </div>

                  <pre className="p-3 bg-[#050505] rounded border border-[#262626] text-[11px] font-mono text-[#D4D4D8] max-h-44 overflow-y-auto leading-relaxed">
                    {JSON.stringify(selectedSpan.attributes || {}, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-[#262626] flex justify-end shrink-0">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setSelectedTrace(null)}
              >
                Close Trace
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
